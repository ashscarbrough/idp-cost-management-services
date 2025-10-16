variable "env" {
  description = "Deployment environment of the solution."
  type        = string
  default     = "dev"
}

variable "sns_contact_email" {
  description = "Email address to subscribe to SNS topic for notifications"
  type        = string
}

variable "tags" {
  description = "The key-value map of strings"
  type        = map(string)
  default     = {}
}

variable "vpc_id" {
  description = "ID of the VPC in which to deploy Lambda functions"
  type        = string
}
