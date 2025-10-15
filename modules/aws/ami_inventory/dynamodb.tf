# #### AMI DDB TABLE #### #
resource "aws_dynamodb_table" "ami_inventory_table" {
  name         = "ami-inventory"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "ResourceId"

  attribute {
    name = "ResourceId"
    type = "S"
  }

  tags = {
    Name        = "ami-inventory"
    Environment = var.env
  }
}
