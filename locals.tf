locals {
  short_region_map = {
    "us-west-2" = "uswe2"
    "us-east-1" = "usea1"
    "us-east-2" = "usea2"
    "us-west-1" = "uswe1"
  }

  short_region = lookup(local.short_region_map, var.aws_region, "unknown")
}
 