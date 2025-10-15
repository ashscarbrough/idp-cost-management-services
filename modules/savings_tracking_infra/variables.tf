variable "account_id" {
  description = "The AWS Account ID where the resources will be deployed"
  type        = string
}

variable "env" {
  description = "The environment for the resources"
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
