variable "active_regions" {
  description = "List of AWS regions to deploy resources to"
  type        = string
  default     = "us-west-1, us-west-2, us-east-1, us-east-2"
}

variable "aws_region" {
  description = "AWS region in which to deploy."
  type        = string
  default     = "us-east-1"
}

variable "cross_account_inventory_role_name" {
  description = "Name of the role to assume in target accounts to perform resource cleanup"
  type        = string
}

variable "cross_account_cleanup_role_name" {
  description = "Name of the role to assume in target accounts to perform resource cleanup"
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

variable "management_account_role_arn" {
  description = "ARN of the role to assume in the management account to read AWS Organization details"
  type        = string
}

variable "multi_account_mode" {
  description = "Enable multi-account mode - requires a read-only role in the AWS management account to pull account details from AWS Organizations"
  type        = bool
  default     = false
}

variable "sns_contact_email" {
  description = "Email address to subscribe to SNS topic for notifications"
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
  default = {
    owner-product-name = "Engineering-Platform",
    cost-department    = "ENG",
    contact-email      = "ash.scarbrough@gmail.com",
    creator-name       = "Ash Scarbrough",
  }
}

variable "vpc_id" {
  description = "ID of the VPC in which to deploy Lambda functions"
  type        = string
}
