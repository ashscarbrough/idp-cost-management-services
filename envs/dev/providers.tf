provider "aws" {
  region = var.aws_region
  default_tags {
    tags = merge(
      {
        env = var.env,
      },
      var.tags
    )
  }
}
