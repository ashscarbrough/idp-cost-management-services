terraform {
  backend "s3" {
    bucket         = "terraform-state-ascarbrough"
    key            = "prod/idp-cost-management-services/prod.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-state-locks"
    encrypt        = true
  }
}