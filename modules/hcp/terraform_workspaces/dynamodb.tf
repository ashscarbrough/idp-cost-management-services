# #### TERRAFORM WORKSPACE DDB TABLE #### #
resource "aws_dynamodb_table" "terraform_workspace_table" {
  name         = "terraform-workspace-table"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "WorkspaceId"

  attribute {
    name = "WorkspaceId"
    type = "S"
  }

  tags = {
    Name        = "terraform-workspace-table"
    Environment = var.env
  }
}