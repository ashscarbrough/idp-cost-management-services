
# ######  TERRAFORM WORKSPACES Lambda  ######
data "archive_file" "terraform_workspaces_lambda_code" {
  type        = "zip"
  source_file = "${path.module}/lambda_code/lambda_function.py"
  output_path = "terraform_workspaces.zip"
}

resource "aws_lambda_function" "terraform_workspaces_lambda_function" {
  depends_on = [
    aws_iam_role.terraform_workspace_inventory_role
  ]
  function_name = "terraform-workspaces-${var.short_region}-${var.env}"
  role          = aws_iam_role.terraform_workspace_inventory_role.arn

  description = "Lambda function to delete unused terraform workspaces."
  environment {
    variables = {
      ENV                       = var.env,
      SECRET_NAME               = var.secret_name,
      SECRET_REGION             = var.secret_region,
      HCP_ORG_ID                = var.hcp_organization_id,
      SNS_ARN                   = var.sns_topic_arn,
      TERRAFORM_WORKSPACE_TABLE = aws_dynamodb_table.terraform_workspace_table.name,
    }
  }

  handler     = "lambda_function.lambda_handler"
  layers      = [var.requests_layer_arn]
  memory_size = 256
  runtime     = "python3.13"

  filename         = data.archive_file.terraform_workspaces_lambda_code.output_path
  source_code_hash = data.archive_file.terraform_workspaces_lambda_code.output_base64sha256

  tags = merge(
    var.tags,
    { Name = "terraform-workspaces-lambda-function" }
  )
  timeout = 900
  vpc_config {
    security_group_ids = [var.lambda_security_group_id]
    subnet_ids         = var.subnet_ids
  }
}


resource "aws_lambda_function_event_invoke_config" "terraform_workspaces_failure_event" {
  function_name          = aws_lambda_function.terraform_workspaces_lambda_function.function_name
  maximum_retry_attempts = 0

  destination_config {
    on_failure {
      destination = var.sns_topic_arn
    }
  }
}