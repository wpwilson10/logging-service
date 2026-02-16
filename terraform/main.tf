##########################################################################
# SNS - topic and subsciption that send notification email for error logs
##########################################################################

resource "aws_sns_topic" "this" {
  name = "${var.project_name}-Error-Logs"
}

resource "aws_sns_topic_subscription" "this" {
  topic_arn = aws_sns_topic.this.arn
  protocol  = "email"
  endpoint  = var.sns_destination_email
}

###########################################################################
# CloudWatch Logs - per-service log groups; streams created by Lambda
###########################################################################

resource "aws_cloudwatch_log_group" "service" {
  for_each          = toset(var.known_services)
  name              = "${var.log_group_prefix}/${each.value}"
  retention_in_days = 90
}

data "aws_caller_identity" "current" {}

##################################################################################################
# Lambda function - Saving log messages from clients to CW Logs and triggering SNS for error logs
##################################################################################################

module "logger_lambda" {
  source        = "terraform-aws-modules/lambda/aws"
  version       = "7.17.0"
  handler       = local.lambda_handler
  runtime       = local.lambda_runtime
  architectures = local.lambda_architecture

  function_name                     = "${var.project_name}-Function"
  description                       = "Logs messages from client service to CW Logs and send notifications for ERROR or FATAL via SNS"
  source_path                       = var.lambda_file_directory
  publish                           = true
  cloudwatch_logs_retention_in_days = 90

  # matches variables used in function code
  environment_variables = {
    LOG_GROUP_PREFIX = var.log_group_prefix
    RETENTION_DAYS   = "90"
    SNS_TOPIC_ARN    = aws_sns_topic.this.arn
    SECRET_TOKEN     = var.secret_token
  }

  # allow API Gateway to call the function
  allowed_triggers = {
    APIGatewayLights = {
      service    = "apigateway"
      source_arn = "${data.aws_apigatewayv2_api.this.execution_arn}/*/*"
    }
  }

  # permissions for saving logs to our CW Logs and publish messages via SNS
  attach_policy_statements = true
  policy_statements = {
    logs_manage = {
      effect = "Allow",
      actions = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:PutRetentionPolicy"
      ],
      resources = [
        "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:${var.log_group_prefix}/*"
      ]
    },
    sns_publish = {
      effect    = "Allow",
      actions   = ["sns:Publish"],
      resources = [aws_sns_topic.this.arn]
    }
  }
}

#############################################################################
# API Gateway - Imports shared gateway and adds lambda function integrations
#############################################################################

data "aws_apigatewayv2_api" "this" {
  api_id = var.api_gateway_id
}

resource "aws_apigatewayv2_integration" "post" {
  api_id                 = data.aws_apigatewayv2_api.this.id
  integration_type       = "AWS_PROXY" # for lambda functions
  integration_uri        = module.logger_lambda.lambda_function_invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "post" {
  api_id    = data.aws_apigatewayv2_api.this.id
  route_key = "POST /${var.api_route}"
  target    = "integrations/${aws_apigatewayv2_integration.post.id}"
}
