data "aws_availability_zones" "available" {}
data "aws_caller_identity" "current" {}

data "aws_secretsmanager_secret_version" "github_token_secret_version" {
  secret_id = "github_token"
}

data "aws_secretsmanager_secret_version" "terraform_token_secret_version" {
  secret_id = "your-secret-name" # Or use arn = "arn:aws:secretsmanager:..."
}