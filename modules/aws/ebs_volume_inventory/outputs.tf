output "detached_ebs_volume_inventory_table_name" {
  value       = aws_dynamodb_table.detached_ebs_volumes_inventory_table.id
  description = "Name of the DynamoDB table for detached EBS volume inventory"
}

output "detached_ebs_volume_inventory_table_arn" {
  value       = aws_dynamodb_table.detached_ebs_volumes_inventory_table.arn
  description = "ARN of the DynamoDB table for detached EBS volume inventory"
}
