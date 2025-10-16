output "s3_storage_bucket_name" {
  description = "S3 bucket name for storing reports and logs"
  value       = aws_s3_bucket.account_storage_bucket.bucket
}

output "s3_storage_bucket_arn" {
  description = "S3 bucket arn for storing reports and logs"
  value       = aws_s3_bucket.account_storage_bucket.arn
}

output "resource_cleanup_savings_table_name" {
  description = "DynamoDB table name for resource cleanup savings"
  value       = aws_dynamodb_table.resource_cleanup_savings_table.id
}

output "resource_cleanup_savings_table_arn" {
  description = "DynamoDB table arn for resource cleanup savings"
  value       = aws_dynamodb_table.resource_cleanup_savings_table.arn
}
