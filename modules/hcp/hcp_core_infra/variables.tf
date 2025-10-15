variable "env" {
  description = "The environment for the resources (e.g. dev, test, prod)"
  type        = string
  default     = "dev"
}

variable "tags" {
  description = "The key-value map of strings"
  type        = map(string)
  default     = {}
}
