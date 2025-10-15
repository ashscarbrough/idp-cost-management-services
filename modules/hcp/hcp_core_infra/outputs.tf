output "terraform_service_account_secret_arn" {
  description = "ARN of the Secrets Manager secret for the Terraform service account token"
  value       = aws_secretsmanager_secret.terraform_service_account_token.arn
}
