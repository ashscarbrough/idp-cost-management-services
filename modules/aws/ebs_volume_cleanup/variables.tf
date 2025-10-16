variable "account_table_name" {
  description = "Name of the DynamoDB table to store AWS accounts"
  type        = string
}

variable "account_table_arn" {
  description = "ARN of the DynamoDB table to store AWS accounts"
  type        = string
}

variable "cleanup_savings_table_arn" {
  description = "ARN of the DynamoDB table to store cleanup savings"
  type        = string
}

variable "cleanup_savings_table_name" {
  description = "Name of the DynamoDB table to store cleanup savings"
  type        = string
  default     = "resource-cleanup-savings"
}

variable "cross_account_cleanup_role_name" {
  description = "Name of the IAM role to assume in target accounts"
  type        = string
}

variable "ebs_volume_table_name" {
  description = "Name of the DynamoDB table to store EBS volume information"
  type        = string
}

variable "ebs_volume_table_arn" {
  description = "ARN of the DynamoDB table to store EBS volume information"
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

variable "tags" {
  description = "The key-value map of strings"
  type        = map(string)
  default     = {}
}

variable "sns_topic_arn" {
  description = "ARN of the SNS topic for notifications of errors and updates"
  type        = string
}
