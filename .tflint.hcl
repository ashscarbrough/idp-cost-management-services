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

  rules = {
    terraform_required_providers = true   # warn if provider version missing
    terraform_required_version    = true   # ensure terraform { required_version = ... } present
    terraform_unused_declarations = true   # detect unused variables/outputs
    terraform_deprecated_interpolation = true # catch legacy "${var}" style
  }
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

  # Common AWS rule customizations
  rules = {
    aws_instance_invalid_type                = true
    aws_instance_previous_type               = true
    aws_s3_bucket_versioning_enabled         = true
    aws_s3_bucket_encryption_enabled         = true
    aws_db_instance_backup_retention_period  = true
    aws_elb_invalid_type                     = true
    aws_iam_policy_invalid_action            = true
    aws_iam_policy_invalid_resource          = true
  }
}

# ------------------------------------------------------------------------------
# (Optional) Ignore specific rules project-wide
# ------------------------------------------------------------------------------
# ignore "aws_instance_previous_type" {
#   reason = "Legacy EC2 type allowed temporarily for migration"
# }