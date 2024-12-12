import os
import json
from typing import Any
import boto3
import time
import logging

# Logger for debugging
logger: logging.Logger = logging.getLogger()
logger.setLevel(level=logging.INFO)

# Initialize CloudWatch Logs client and SNS client
# Done globally allowing more efficient subsequent invocations/warn starts
cloudwatch_logs_client = boto3.client(service_name="logs")
sns_client = boto3.client(service_name="sns")

# Load environment variables
LOG_GROUP_NAME = os.environ.get("LOG_GROUP_NAME", "Default_Group")
LOG_STREAM_NAME = os.environ.get("LOG_STREAM_NAME", "Default_Stream")
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "Default_Topic")
SECRET_TOKEN = os.environ.get("SECRET_TOKEN", "default-secret-token")


def log_to_cloudwatch(log_entry: dict[str, Any]) -> None:
    """
    Sends a structured log entry to CloudWatch Logs.

    Args:
        log_entry (dict): The log entry in structured JSON format.
    """
    try:
        # Construct the log event with timestamp and message
        log_event: dict[str, Any] = {
            "timestamp": int(time.time() * 1000),  # Milliseconds since epoch
            "message": json.dumps(log_entry),  # Convert dict to JSON string for logging
        }

        # Send the log event to CloudWatch
        kwargs: dict[str, Any] = {
            "logGroupName": LOG_GROUP_NAME,
            "logStreamName": LOG_STREAM_NAME,
            "logEvents": [log_event],
        }

        cloudwatch_logs_client.put_log_events(**kwargs)

    except Exception as e:
        logger.error(msg=f"Failed to send log to CloudWatch: {e}")


def notify_error_sns(log_entry: dict[str, Any]) -> None:
    """
    Sends an SNS notification if the log level is ERROR or FATAL.
    This version dynamically checks for existing fields in the log entry and formats them into a message.

    Args:
        log_entry (dict): The log entry containing the message and level.
    """
    # Check if the level is ERROR or FATAL
    level = log_entry.get("level", "").upper()
    if level not in ["ERROR", "FATAL"]:
        return

    try:
        # Dynamically format the log entry into a human-readable message
        message_parts: list[str] = []

        # Loop through the log entry and include only the fields that exist
        for key, value in log_entry.items():
            if value:  # Only include non-empty fields
                # Format each field as "Key: Value"
                message_parts.append(f"{key.replace('_', ' ').title()}: {value}")

        # Join all the parts into a single string, each part on a new line
        message: str = "\n".join(message_parts)

        # Send the SNS notification with the formatted message
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f"AWS Service {log_entry['level']} Notification",
            Message=message,  # Send the formatted message
        )

    except Exception as e:
        logger.error(f"Error sending SNS message: {e}")


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    AWS Lambda function entry point.

    Parses a log message sent from some client service and writes it to CloudWatch Logs.

    Args:
        event (dict): The input event to the Lambda function (contains the log message).
        context (LambdaContext): The runtime information of the Lambda function.
    """
    # Check the custom header for the pre-shared token
    headers = event.get("headers", {})
    # Lowercase is important for HTTP 2 protocol
    token = headers.get("x-custom-auth")

    # Validate the token
    if token != SECRET_TOKEN:
        logger.info(msg="Denied unauthorized request")
        return {"statusCode": 403, "body": "Unauthorized"}

    # Parse the incoming request body
    try:
        body = json.loads(event.get("body", "{}"))

        log_to_cloudwatch(body)
        notify_error_sns(body)

        return {
            "statusCode": 200,
            "body": json.dumps(obj={"message": "Log saved to CloudWatch."}),
        }
    except json.JSONDecodeError:
        logger.error(msg="Failed to parse request body.")
        return {
            "statusCode": 400,
            "body": json.dumps(obj={"error": "Invalid JSON format."}),
        }
    except Exception as e:
        logger.error(msg=f"Error processing log: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps(obj={"error": "Internal server error."}),
        }
