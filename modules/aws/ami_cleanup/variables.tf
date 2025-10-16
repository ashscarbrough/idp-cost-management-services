variable "account_table_name" {
  description = "Name of the DynamoDB table to store AWS accounts"
  type        = string
  default     = "aws-accounts"
}

variable "account_table_arn" {
  description = "ARN of the DynamoDB table to store AWS accounts"
  type        = string
}

variable "ami_table_name" {
  description = "Name of the DynamoDB table to store AMI inventory"
  type        = string
  default     = "ami-inventory"
}

variable "ami_table_arn" {
  description = "ARN of the DynamoDB table to store AMI inventory"
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
  description = "Name of the role to assume in target accounts to perform resource cleanup"
  type        = string
  default     = "cloud-resource-management-role"
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
