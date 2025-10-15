# ------------------------------------------------------------------------------
# Global settings
# ------------------------------------------------------------------------------
config {
  format = "default"     # 'default', 'json', or 'checkstyle'
  call_module_type = "all" # scan all modules, not just root
}

# ------------------------------------------------------------------------------
# Terraform plugin
# ------------------------------------------------------------------------------
plugin "terraform" {
  enabled = true
  preset  = "recommended"
}

rule "terraform_required_providers" {
  enabled = true   # warn if provider version missing
}

rule "terraform_required_version" {
  enabled = true   # ensure terraform { required_version = ... } present
}

rule "terraform_unused_declarations" {
  enabled = true   # detect unused variables/outputs
}

rule "terraform_deprecated_interpolation" {
  enabled = true   # catch legacy "${var}" style
}

# ------------------------------------------------------------------------------
# AWS plugin
# ------------------------------------------------------------------------------
plugin "aws" {
  enabled = true
  version = "0.30.0" # pin to a stable release (see https://github.com/terraform-linters/tflint-ruleset-aws/releases)
  source  = "github.com/terraform-linters/tflint-ruleset-aws"

  # Optional: restrict region if desired
  # region = "us-east-1"
}

# Common AWS rule customizations
rule "aws_instance_invalid_type" {
  enabled = true
}

rule "aws_instance_previous_type" {
  enabled = true
}

rule "aws_iam_policy_invalid_action" {
  enabled = true
}

rule "aws_iam_policy_invalid_resource" {
  enabled = true
}

# ------------------------------------------------------------------------------
# (Optional) Ignore specific rules project-wide
# ------------------------------------------------------------------------------
# ignore "aws_instance_previous_type" {
#   reason = "Legacy EC2 type allowed temporarily for migration"
# }