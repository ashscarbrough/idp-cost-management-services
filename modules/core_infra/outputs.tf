output "idp_automation_sns_topic" {
  description = "SNS topic for notications regarding IDP Automation solution"
  value       = aws_sns_topic.idp_automation_topic.arn
}

output "account_table_name" {
  description = "DynamoDB table name for AWS accounts"
  value       = aws_dynamodb_table.aws_accounts.id
}

output "account_table_arn" {
  description = "DynamoDB table ARN for AWS accounts"
  value       = aws_dynamodb_table.aws_accounts.arn
}

output "account_table_hash_key" {
  description = "DynamoDB table hash key for AWS accounts"
  value       = aws_dynamodb_table.aws_accounts.hash_key
}

output "lambda_security_group_id" {
  description = "Security Group ID attached to the Lambda function"
  value       = aws_security_group.idp_automation_lambda_sg.id
}
