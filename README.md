# logging-service

AWS based service for remote logging

# Description

This project implements a REST endpoint allowing clients to remotely log messages for persistent storage, discoverablity, and proactive notification of errors. It includes Terraform configuration and AWS Lambda functions designed to log messages to AWS CloudWatch Logs and send notifications via SNS (Simple Notification Service) for error-level logs.

This project is intended to be intergrated with the AWS Infrastructure provisioned from [WpwilsonSite](https://github.com/wpwilson10/WpwilsonSite), but can be used with any AWS environment with an HTTP API Gateway.

The architecture for this project follows [AWS's RESTful microservices scenario](https://docs.aws.amazon.com/wellarchitected/latest/serverless-applications-lens/restful-microservices.html) which is a serverless application framework and part of AWS's recommended Well-Architected Framework. By using an API Gateway which calls Lambda functions, this solution is scalable, distributed, and fault-tolerant by default.

![Architecture](./diagram.svg)

## Setup

### Configuration

Create a terraform.tfvars file under ./terraform and configure as desired.

Required variables:

-   api_gateway - the ID of the API Gateway with which this service integrates
-   sns_destination_email - the email that receives error notifications.
-   secret_token - a secret token used to authenticate calls from appropriate clients

See variables.tf for more information.

### Deploy

Once the configuration above is complete, run the following commands from the ./terraform directory.

```
terraform init
terraform plan
terraform apply
```

Before using this service, the email associated with sns_destination_email will need to be verified so that it can receive notifications.

## Usage

To call this service, the client will need to send an HTTP POST request to the endpoint exposed by the API Gateway with a request like:

```
POST https://your-lambda-url.amazonaws.com/logging

Headers:
  x-custom-auth: <your-secret-token>

Body:
{
  "message": "An error occurred",
  "level": "ERROR"
}
```

### Headers:

x-custom-auth: A custom header containing a pre-shared token. This token is used by the Lambda function to authenticate the request. The token sent by the client should match the previously configured secret_token variable, or the request will be rejected with a 403 Unauthorized status.

### Body (JSON format):

The body must be a valid JSON struct, but otherwise there are no required fields. For SNS messaging to occur, there must be a top level "level" field indicating the log level.

level (optional): The log level for the message. This can be any of the predefined log levels such as "INFO", "ERROR", or "FATAL". If the level is "ERROR" or "FATAL", the service will also send an SNS notification to alert other systems or administrators.

message (optional): The actual log message that needs to be sent (e.g., "An error occurred").

The example body below would be just as valid:

```
{
  "timestamp": "2024-12-12T08:45:30Z",
  "level": "ERROR",
  "message": "An error occurred while processing the payment",
  "client_name": "PaymentService",
  "request_id": "12345678-1234-5678-1234-567812345678",
  "error_code": "PAYMENT_FAILED",
  "function_name": "process_payment",
  "host_name": "payment-service-prod-01",
  "environment": "production",
  "trace_id": "abcd1234-5678-90ef-1234-567890abcdef",
  "service_name": "payment-service"
}
```
