variable "env" {
  description = "Deployment environment of the solution."
  type        = string
  default     = "dev"
}

variable "hcp_organization_id" {
  description = "HCP Organization ID"
  type        = string
}

variable "lambda_security_group_id" {
  description = "Security Group ID to attach to the Lambda function"
  type        = string
}

variable "requests_layer_arn" {
  description = "ARN of the Lambda layer containing the requests library"
  type        = string
}

variable "secret_name" {
  description = "Name of the Secrets Manager secret containing the HCP API token"
  type        = string
}

variable "secret_region" {
  description = "AWS region where the Secrets Manager secret is stored"
  type        = string
  default     = "us-west-2"
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
