output "ami_inventory_table_name" {
  value       = aws_dynamodb_table.ami_inventory_table.name
  description = "The name of the DynamoDB table to store AMI inventory"
}

output "ami_inventory_table_arn" {
  value       = aws_dynamodb_table.ami_inventory_table.arn
  description = "The ARN of the DynamoDB table to store AMI inventory"
}
