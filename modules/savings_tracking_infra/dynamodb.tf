# #### Resource Cleanup Savings TABLE #### #
resource "aws_dynamodb_table" "resource_cleanup_savings_table" {
  name         = "resource-cleanup-savings"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "ResourceId"

  attribute {
    name = "ResourceId"
    type = "S"
  }

  tags = {
    Name        = "resource-cleanup-savings"
    Environment = var.env
  }
}
