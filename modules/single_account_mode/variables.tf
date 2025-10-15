variable "dynamodb_accounts_table_name" {
  description = "Name of the DynamoDB table to store AWS accounts"
  type        = string
  default     = "aws-accounts"
}

variable "dynamodb_accounts_table_hash_key" {
  description = "Hash key of the DynamoDB table to store AWS accounts"
  type        = string
  default     = "account_id"
}

variable "env" {
  description = "Deployment environment of the solution."
  type        = string
  default     = "dev"
}

variable "target_account_id" {
  description = "AWS account ID in which to deploy solution"
  type        = string
}
