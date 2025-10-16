locals {
  short_region_map = {
    "us-west-2" = "uswe2"
    "us-east-1" = "usea1"
    "us-east-2" = "usea2"
    "us-west-1" = "uswe1"
  }

  short_region = lookup(local.short_region_map, var.aws_region, "unknown")

  deployment_account_id = data.aws_caller_identity.current.account_id
}
 