
variable "active_regions" {
  description = "Comma-separated list of AWS regions to inventory EBS snapshots in"
  type        = string
  default     = "us-west-2,us-east-1,eu-west-1,eu-west-2,eu-central-1,ap-southeast-1"
}

variable "account_table_arn" {
  description = "ARN of the DynamoDB table to store AWS accounts"
  type        = string
}

variable "account_table_name" {
  description = "Name of the DynamoDB table to store AWS accounts"
  type        = string
}

variable "cross_account_inventory_role_name" {
  description = "Name of the IAM role to assume in target accounts"
  type        = string
}

variable "env" {
  description = "Deployment environment of the solution."
  type        = string
  default     = "dev"
}

variable "lambda_security_group_id" {
  description = "Security Group ID to attach to the Lambda function"
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
