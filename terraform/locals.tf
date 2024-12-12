locals {
  lambda_runtime      = "python3.13"
  lambda_architecture = ["arm64"]
  lambda_handler      = "lambda_function.lambda_handler"         # https://docs.aws.amazon.com/lambda/latest/dg/python-handler.html
  cw_logs_full_arn    = "${aws_cloudwatch_log_group.this.arn}:*" # https://github.com/hashicorp/terraform-provider-aws/issues/22957
}
