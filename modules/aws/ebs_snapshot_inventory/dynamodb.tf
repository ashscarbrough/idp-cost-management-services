# #### EBS SNAPSHOT DDB TABLE #### #
resource "aws_dynamodb_table" "ebs_snapshot_table" {
  name         = "snapshot-deletion-schedule"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "ResourceId"

  attribute {
    name = "ResourceId"
    type = "S"
  }

  tags = {
    Name        = "ebs-snapshot-table"
    Environment = var.env
  }
}
