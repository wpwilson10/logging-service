variable "api_gateway_id" {
  description = "ID of the API Gateway created in WpwilsonSite repository"
  type        = string
}

variable "api_route" {
  description = "API route for this service (e.g. api_domain_prefix.domain_name.com/api_route)"
  type        = string
  default     = "logging"
}

# Uses the access credential values in the profile located at
#  "~/.aws/credentials" (Linux) or "%USERPROFILE%\.aws\credentials" (Windows).
# See https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html
variable "credentials_profile" {
  description = "Profile to use from the AWS credentials file"
  type        = string
  default     = "default"
}

variable "lambda_file_directory" {
  description = "Relative location of the directory containing files for Lambda function"
  type        = string
  default     = "../aws"
}

variable "project_name" {
  description = "Name for this project which will be prepended to new resources"
  type        = string
  default     = "Logging-Demo"
}

variable "region" {
  description = "AWS Region to use for this account"
  type        = string
  default     = "us-east-1"
}

variable "secret_token" {
  description = "Shared secret token used to authenticate calls form microcontroller to AWS"
  type        = string
}

variable "sns_destination_email" {
  description = "Email address used as SNS subscription endpoint to send error notifications"
  type        = string
}

