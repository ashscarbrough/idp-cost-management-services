variable "account_table_name" {
  description = "Name of the DynamoDB table to store AWS accounts"
  type        = string
  default     = "aws-accounts"
}

variable "account_table_arn" {
  description = "ARN of the DynamoDB table to store AWS accounts"
  type        = string
}

variable "active_regions" {
  description = "List of AWS regions to scan for AMIs"
  type        = string
  default     = "us-west-2, us-east-1, us-east-2,us-west-1"
}

variable "cross_account_inventory_role_name" {
  description = "Name of the role to assume in target accounts to perform resource cleanup"
  type        = string
}

variable "env" {
  description = "Deployment environment of the solution."
  type        = string
  default     = "dev"
}

variable "short_region" {
  description = "Short region code (e.g., usw2 for us-west-2)"
  type        = string
}

variable "sns_topic_arn" {
  description = "ARN of the SNS topic for notifications of errors and updates"
  type        = string
}

variable "tags" {
  description = "The key-value map of strings"
  type        = map(string)
  default     = {}
}
