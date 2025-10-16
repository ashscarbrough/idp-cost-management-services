# #### AMI DDB TABLE #### #
resource "aws_dynamodb_table" "ami_inventory_table" {
  name         = "ami-inventory-${var.env}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "ResourceId"

  attribute {
    name = "ResourceId"
    type = "S"
  }

  tags = var.tags
}
