resource "aws_secretsmanager_secret" "terraform_service_account_token" {
  name = "terraform-service-account-token"
  tags = var.tags
}
