# #### AWS ACCOUNT DDB TABLE #### #
resource "aws_dynamodb_table" "aws_accounts" {
  name         = "aws-accounts-${var.env}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "AccountId"

  attribute {
    name = "AccountId"
    type = "S"
  }

  attribute {
    name = "AccountName"
    type = "S"
  }

  global_secondary_index {
    name               = "AccountName-index"
    hash_key           = "AccountName"
    projection_type    = "INCLUDE"
    non_key_attributes = ["GlobalRegion", "Environment"]
  }

  tags = var.tags
}
