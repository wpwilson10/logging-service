import os
import json
from typing import Any
import boto3
import time
import logging


# Logger for debugging
logger: logging.Logger = logging.getLogger()
logger.setLevel(level=logging.INFO)


def log_to_cloudwatch(message: str, level: str) -> None:
    """
    Sends a log entry to CloudWatch Logs.

    Args:
        message (str): The log message.
        level (str): The log level (e.g., INFO, ERROR).
    """
    log_event: dict[str, Any] = {
        "timestamp": int(time.time() * 1000),  # Milliseconds since epoch
        "message": f"{level} | {message}",
    }

    try:
        # Set up the boto3 client for CloudWatch Logs
        cloudwatch_logs_client = boto3.client(service_name="logs")

        # Construct the put_log_events request
        kwargs: dict[str, Any] = {
            "logGroupName": os.environ.get("LOG_GROUP_NAME", default="Default_Group"),
            "logStreamName": os.environ.get(
                "LOG_STREAM_NAME", default="Default_Stream"
            ),
            "logEvents": [log_event],
        }

        # Send the log event
        cloudwatch_logs_client.put_log_events(**kwargs)

    except Exception as e:
        logger.error(msg=f"Failed to send log to CloudWatch: {e}")


def notify_error_SNS(message: str, level: str) -> None:
    """
    Sends the log message via an SNS notification if the level is ERROR or FATAL

    Args:
        message (str): The log message.
        level (str): The log level (e.g., INFO, ERROR).
    """
    if level not in ("ERROR", "FATAL"):
        return

    try:
        # Read environment variables
        SNS_TOPIC_ARN: str = os.environ.get("SNS_TOPIC_ARN", default="Default_Topic")
        AWS_REGION: str = os.environ.get("AWS_REGION", default="us-east-1")

        # Initialize the SNS client
        sns_client = boto3.client(service_name="sns", region_name=AWS_REGION)

        # Send the message
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject="AWS Service Error Notification",
            Message=message,
        )
    except Exception as e:
        logger.error(msg=f"Error sending SNS message: {e}")


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
    if token != os.environ.get("SECRET_TOKEN"):
        logger.info(msg="Denied unauthorized request")
        return {"statusCode": 403, "body": "Unauthorized"}

    # Parse the incoming request body
    try:
        body = json.loads(event.get("body", "{}"))
        message = body.get("message", "No message provided")
        level = body.get("level", "INFO").upper()

        log_to_cloudwatch(message=message, level=level)
        notify_error_SNS(message=message, level=level)

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
