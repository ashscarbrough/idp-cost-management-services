# #### Resource Cleanup Savings TABLE #### #
resource "aws_dynamodb_table" "resource_cleanup_savings_table" {
  name         = "resource-cleanup-savings-${var.env}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "ResourceId"

  attribute {
    name = "ResourceId"
    type = "S"
  }

  tags = var.tags
}
