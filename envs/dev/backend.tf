terraform {
  backend "s3" {
    bucket         = "terraform-state-ascarbrough"
    key            = "dev/idp-cost-management-services/dev.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-state-locks"
    encrypt        = true
  }
}