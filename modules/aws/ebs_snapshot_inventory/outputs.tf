output "ebs_snapshot_dynamodb_table_name" {
  description = "DynamoDB table name for EBS snapshot inventory"
  value       = aws_dynamodb_table.ebs_snapshot_table.id
}

output "ebs_snapshot_dynamodb_table_arn" {
  description = "DynamoDB table ARN for EBS snapshot inventory"
  value       = aws_dynamodb_table.ebs_snapshot_table.arn
}
