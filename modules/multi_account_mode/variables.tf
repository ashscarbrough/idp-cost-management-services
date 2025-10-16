variable "dynamodb_accounts_table_name" {
  description = "Name of the DynamoDB table to store AWS accounts"
  type        = string
}

variable "dynamodb_accounts_table_arn" {
  description = "ARN of the DynamoDB table to store AWS accounts"
  type        = string
}

variable "env" {
  description = "Deployment environment of the solution."
  type        = string
  default     = "dev"
}

variable "inactive_accounts_list" {
  description = "List of AWS account IDs to exclude from the accounts table"
  type        = string
  default     = ""
}

variable "lambda_security_group_id" {
  description = "Security Group ID to attach to the Lambda function"
  type        = string
}

variable "management_account_role_arn" {
  description = "ARN of the role to assume in the management account to read AWS Organization details"
  type        = string
}

variable "short_region" {
  description = "Short region code (e.g., usw2 for us-west-2)"
  type        = string
}

variable "sns_topic_arn" {
  description = "ARN of the SNS topic for notifications of errors and updates"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs within the VPC to deploy Lambda functions"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "The key-value map of strings"
  type        = map(string)
  default     = {}
}
