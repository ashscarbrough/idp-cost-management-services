output "terraform_workspace_table_name" {
  description = "DynamoDB table name for Terraform Workspaces"
  value       = aws_dynamodb_table.terraform_workspace_table.name
}
