# logging-service

AWS-based service for remote logging with per-service log routing.

## Description

This project implements a REST endpoint allowing clients to remotely log messages for persistent storage, discoverability, and proactive notification of errors. It includes Terraform configuration and an AWS Lambda function that routes logs into per-service CloudWatch Log Groups and per-client Log Streams, and sends SNS notifications for error-level logs.

Logs are organized under a configurable prefix (default `/wpwilson/`) with automatic routing:

```
/wpwilson/
├── wpwilsonsite/          ← Log group for frontend errors
│   └── browser/           ← Log stream (from client_name)
├── sunrise-lamp-aws/      ← Log group for Pico W
│   └── Sunrise Lamp/      ← Log stream per device
└── (new-service)/         ← Auto-created when a new service_name appears
```

This project integrates with the AWS infrastructure provisioned from [AWS_Web_Hosting_Infra](https://github.com/wpwilson10/AWS_Web_Hosting_Infra), but can be used with any AWS environment with an HTTP API Gateway.

The architecture follows [AWS's RESTful microservices scenario](https://docs.aws.amazon.com/wellarchitected/latest/serverless-applications-lens/restful-microservices.html), a serverless application framework and part of AWS's recommended Well-Architected Framework. By using an API Gateway which calls Lambda functions, this solution is scalable, distributed, and fault-tolerant by default.

![Architecture](./diagram.svg)

## Setup

### Configuration

Create a `terraform.tfvars` file under `./terraform` and configure as desired.

Required variables:

- `api_gateway_id` — the ID of the API Gateway with which this service integrates
- `sns_destination_email` — the email that receives error notifications
- `secret_token` — a secret token used to authenticate calls from appropriate clients

Optional variables:

- `log_group_prefix` — CloudWatch log group prefix (default: `/wpwilson`)
- `known_services` — list of service names to pre-create log groups for (default: `["wpwilsonsite", "sunrise-lamp-aws"]`)

See `variables.tf` for more information.

### Deploy

Once the configuration above is complete, run the following commands from the `./terraform` directory.

```bash
terraform init
terraform plan
terraform apply
```

Before using this service, the email associated with `sns_destination_email` will need to be confirmed so that it can receive notifications.

## Usage

To call this service, the client sends an HTTP POST request to the endpoint exposed by the API Gateway:

```
POST https://api.wpwilson.com/logging

Headers:
  content-type: application/json
  x-custom-auth: <your-secret-token>

Body:
{
  "service_name": "sunrise-lamp-aws",
  "client_name": "Sunrise Lamp",
  "level": "ERROR",
  "message": "An error occurred"
}
```

### Headers

`x-custom-auth` — A pre-shared token used by the Lambda function to authenticate the request. Must match the configured `secret_token`, or the request will be rejected with a 403 Unauthorized status.

### Body (JSON)

**Required fields:**

- `service_name` (string) — Identifies the calling service. Used to route the log into the correct CloudWatch Log Group (`{prefix}/{service_name}`). Returns 400 if missing.

**Routing fields:**

- `client_name` (string, optional) — Identifies the specific client or device. Used as the CloudWatch Log Stream name. Falls back to the current date (`YYYY-MM-DD`) if absent.

**Log content fields:**

- `level` (string, optional) — Log level (`INFO`, `ERROR`, `FATAL`, etc.). If `ERROR` or `FATAL`, an SNS notification is sent with the service name in the subject.
- `message` (string, optional) — The log message.

Any additional fields in the JSON body are stored as-is in the CloudWatch log event.

### Example

```json
{
  "service_name": "sunrise-lamp-aws",
  "client_name": "Sunrise Lamp",
  "level": "ERROR",
  "message": "Failed to fetch schedule from API",
  "timestamp": "2026-02-16T04:15:00Z"
}
```

This log would be routed to:
- **Log Group:** `/wpwilson/sunrise-lamp-aws`
- **Log Stream:** `Sunrise Lamp`

And trigger an SNS notification with subject: `sunrise-lamp-aws ERROR Notification`.
