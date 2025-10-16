# This resource adds an initial item to the DynamoDB table for the single account where the solution is deployed.
# This item represents the current account and is required for the solution to function correctly in single account mode.
# The fields are populated with default or empty values, except for AccountId and Environment.
# Adjust the fields as necessary to fit your requirements.
resource "aws_dynamodb_table_item" "DDB_Item_Target_Account" {
  table_name = var.dynamodb_accounts_table_name
  hash_key   = var.dynamodb_accounts_table_hash_key

  item = <<ITEM
  {
    "AccountId": {"S": "${var.target_account_id}"},
    "AccountName": {"S": "${var.target_account_name}"},
    "AccountOwner": {"S": ""},
    "AccountStatus": {"S": "ACTIVE"},
    "Arn": {"S": ""},
    "CostCenter": {"S": ""},
    "CostDepartment": {"S": ""},
    "Custodian": {"S": ""},
    "Email": {"S": ""},
    "Environment": {"S": "${var.env}"},
    "GlobalRegion": {"S": ""},
    "JoinedDatetime": {"S": ""},
    "JoinedMethod": {"S": ""},
    "LastUpdated": {"S": ""},
    "ParentId": {"S": ""},
    "ParentType": {"S": ""}
  }
  ITEM
}
