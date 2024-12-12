output "logging_endpoint" {
  description = "URL of the logging API"
  value       = "${data.aws_apigatewayv2_api.this.api_endpoint}/${var.api_route}"
}
