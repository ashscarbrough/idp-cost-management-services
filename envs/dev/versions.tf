# Individual environments may have specific needs that require
# different provider versions due to features or bug fixes relevant to that env
# If env folder uses other shared modules - this will give you control 
# over version dependencies for each env.

terraform {
  required_version = "~> 1.13.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.15"
    }
  }
}