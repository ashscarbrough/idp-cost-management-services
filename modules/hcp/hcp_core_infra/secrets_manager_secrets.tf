resource "aws_secretsmanager_secret" "terraform_service_account_token" {
  name = "terraform-service-account-token-${var.env}"
  tags = var.tags
}
