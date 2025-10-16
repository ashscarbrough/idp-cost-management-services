########### #### DETACHED EBS VOLUME DDB TABLE #### ###########
resource "aws_dynamodb_table" "detached_ebs_volumes_inventory_table" {
  name         = "detached-ebs-volumes-inventory-${var.env}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "VolumeId"

  attribute {
    name = "VolumeId"
    type = "S"
  }

  tags = {
    Name        = "detached-ebs-volumes-table-${var.env}"
    Environment = var.env
  }
}
