# logging-service

AWS based service for remote logging

# Description

This project implements a REST endpoint allowing clients to remotely log messages for persistent storage, discoverablity, and proactive notification of errors. It includes Terraform configuration and AWS Lambda functions designed to log messages to AWS CloudWatch Logs and send notifications via SNS (Simple Notification Service) for error-level logs.

This project is intended to be intergrated with the AWS Infrastructure provisioned from [WpwilsonSite](https://github.com/wpwilson10/WpwilsonSite), but can be used with any AWS environment with an HTTP API Gateway.

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

message: The actual log message that needs to be sent (e.g., "An error occurred").

level: The log level for the message. This can be any of the predefined log levels such as "INFO", "ERROR", or "FATAL". If the level is "ERROR" or "FATAL", the service will also send an SNS notification to alert other systems or administrators.
