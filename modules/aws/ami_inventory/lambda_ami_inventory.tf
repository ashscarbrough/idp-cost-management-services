
# ######  AMI Inventory Lambda  ######
data "archive_file" "ami_inventory_lambda_code" {
  type        = "zip"
  source_file = "${path.module}/lambda_code/lambda_function.py"
  output_path = "ami_inventory.zip"
}

resource "aws_lambda_function" "ami_inventory_lambda_function" {
  depends_on = [
    aws_iam_role.ami_inventory_role
  ]
  function_name = "ami-inventory-lambda-${var.short_region}-${var.env}"
  role          = aws_iam_role.ami_inventory_role.arn

  description = "Lambda function to scan, document, and inventory amis."
  environment {
    variables = {
      ACCOUNT_TABLE = var.account_table_name,
      ACTIVE_REGIONS = var.active_regions,
      AMI_TABLE  = aws_dynamodb_table.ami_inventory_table.id,
      CROSS_ACCOUNT_ROLE = var.cross_account_inventory_role_name,
      ENV     = var.env,
      SNS_ARN = var.sns_topic_arn
    }
  }

  handler = "lambda_function.lambda_handler"
  memory_size = 2048
  runtime     = "python3.13"

  filename         = data.archive_file.ami_inventory_lambda_code.output_path
  source_code_hash = data.archive_file.ami_inventory_lambda_code.output_base64sha256

  tags = merge(
    var.tags,
    { Name = "ami-inventory-lambda-function" }
  )
  timeout = 900
  vpc_config {
    security_group_ids = [var.lambda_security_group_id]
    subnet_ids         = var.subnet_ids
  }
}

resource "aws_cloudwatch_log_group" "ami_inventory_lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.ami_inventory_lambda_function.function_name}"
  retention_in_days = 30
}

resource "aws_lambda_function_event_invoke_config" "ami_inventory_lambda_failure_event" {
  function_name          = aws_lambda_function.ami_inventory_lambda_function.function_name
  maximum_retry_attempts = 0

  destination_config {
    on_failure {
      destination = var.sns_topic_arn
    }
  }
}