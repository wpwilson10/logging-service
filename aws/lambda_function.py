from __future__ import annotations

import json
import logging
import os
import time
from typing import TYPE_CHECKING, Any, NotRequired, TypedDict

import boto3

if TYPE_CHECKING:
    from mypy_boto3_logs import CloudWatchLogsClient
    from mypy_boto3_logs.type_defs import InputLogEventTypeDef
    from mypy_boto3_sns import SNSClient

# Logger for debugging
logger: logging.Logger = logging.getLogger()
logger.setLevel(level=logging.INFO)

# Initialize CloudWatch Logs client and SNS client
# Done globally allowing more efficient subsequent invocations/warm starts
cloudwatch_logs_client: CloudWatchLogsClient = boto3.client(service_name="logs")  # pyright: ignore[reportUnknownMemberType] -- boto3.client() overload resolution is partially unknown
sns_client: SNSClient = boto3.client(service_name="sns")  # pyright: ignore[reportUnknownMemberType] -- boto3.client() overload resolution is partially unknown

# Load environment variables
LOG_GROUP_PREFIX: str = os.environ.get("LOG_GROUP_PREFIX", "/wpwilson")
RETENTION_DAYS: int = int(os.environ.get("RETENTION_DAYS", "90"))
SNS_TOPIC_ARN: str = os.environ.get("SNS_TOPIC_ARN", "Default_Topic")
SECRET_TOKEN: str = os.environ.get("SECRET_TOKEN", "default-secret-token")


# --- Type definitions ---

# Lambda event from API Gateway v2 — only fields we actually use
LambdaEvent = dict[
    str, Any
]  # API Gateway event shape is large; typed access below narrows it

# Structured log entry received from client services
LogEntry = dict[
    str, str | int | dict[str, str]
]  # JSON log payloads: string/int values plus nested dicts like clientInfo


class LambdaResponse(TypedDict):
    statusCode: int
    body: str
    headers: NotRequired[dict[str, str]]


def ensure_log_group(group_name: str) -> None:
    """Creates a CloudWatch log group if it doesn't already exist and sets retention."""
    try:
        cloudwatch_logs_client.create_log_group(logGroupName=group_name)
        cloudwatch_logs_client.put_retention_policy(
            logGroupName=group_name,
            retentionInDays=RETENTION_DAYS,
        )
    except cloudwatch_logs_client.exceptions.ResourceAlreadyExistsException:
        pass


def ensure_log_stream(group_name: str, stream_name: str) -> None:
    """Creates a CloudWatch log stream if it doesn't already exist."""
    try:
        cloudwatch_logs_client.create_log_stream(
            logGroupName=group_name,
            logStreamName=stream_name,
        )
    except cloudwatch_logs_client.exceptions.ResourceAlreadyExistsException:
        pass


def log_to_cloudwatch(log_entry: LogEntry) -> None:
    """
    Sends a structured log entry to CloudWatch Logs.

    Routes to per-service log groups and per-client log streams:
      Log group:  {LOG_GROUP_PREFIX}/{service_name}
      Log stream: {client_name} or YYYY-MM-DD if client_name absent
    """
    try:
        service_name = str(log_entry["service_name"])
        client_name_raw = log_entry.get("client_name")
        client_name = (
            str(client_name_raw) if client_name_raw else time.strftime("%Y-%m-%d")
        )

        group_name = f"{LOG_GROUP_PREFIX}/{service_name}"

        ensure_log_group(group_name)
        ensure_log_stream(group_name, client_name)

        log_event: InputLogEventTypeDef = {
            "timestamp": int(time.time() * 1000),
            "message": json.dumps(log_entry),
        }

        cloudwatch_logs_client.put_log_events(
            logGroupName=group_name,
            logStreamName=client_name,
            logEvents=[log_event],
        )

    except Exception as e:
        logger.error(msg=f"Failed to send log to CloudWatch: {e}")


def notify_error_sns(log_entry: LogEntry) -> None:
    """
    Sends an SNS notification if the log level is ERROR or FATAL.

    Includes service_name in the subject and client_name in the body
    for quick identification of the error source.
    """
    level_raw = log_entry.get("level", "")
    level = str(level_raw).upper()
    if level not in ["ERROR", "FATAL"]:
        return

    try:
        service_name = str(log_entry.get("service_name", "unknown"))
        client_name_raw = log_entry.get("client_name")

        # Build human-readable message body
        message_parts: list[str] = []
        for key, value in log_entry.items():
            if value:
                message_parts.append(f"{key.replace('_', ' ').title()}: {value}")

        message: str = "\n".join(message_parts)

        subject = f"{service_name} {level} Notification"
        # SNS subject max is 100 characters
        if len(subject) > 100:
            subject = subject[:97] + "..."

        if client_name_raw:
            message = f"Client: {client_name_raw}\n\n{message}"

        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject,
            Message=message,
        )

    except Exception as e:
        logger.error(f"Error sending SNS message: {e}")


def lambda_handler(event: LambdaEvent, context: object) -> LambdaResponse:
    """
    AWS Lambda function entry point.

    Parses a log message sent from some client service and writes it to CloudWatch Logs.
    Requires service_name in the request body for log routing.
    """
    # Check the custom header for the pre-shared token
    headers: dict[str, str] = event.get("headers", {})
    # Lowercase is important for HTTP 2 protocol
    token: str | None = headers.get("x-custom-auth")

    if token != SECRET_TOKEN:
        logger.info(msg="Denied unauthorized request")
        return LambdaResponse(statusCode=403, body="Unauthorized")

    # Parse the incoming request body
    try:
        body: LogEntry = json.loads(event.get("body", "{}"))

        # Validate service_name is present
        service_name = body.get("service_name")
        if not service_name or not isinstance(service_name, str):
            return LambdaResponse(
                statusCode=400,
                body=json.dumps({"error": "Missing required field: service_name"}),
            )

        log_to_cloudwatch(body)
        notify_error_sns(body)

        return LambdaResponse(
            statusCode=200,
            body=json.dumps({"message": "Log saved to CloudWatch."}),
        )
    except json.JSONDecodeError:
        logger.error(msg="Failed to parse request body.")
        return LambdaResponse(
            statusCode=400,
            body=json.dumps({"error": "Invalid JSON format."}),
        )
    except Exception as e:
        logger.error(msg=f"Error processing log: {e}")
        return LambdaResponse(
            statusCode=500,
            body=json.dumps({"error": "Internal server error."}),
        )
