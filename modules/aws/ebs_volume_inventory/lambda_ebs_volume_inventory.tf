
# ######  EBS Cleanup Lambda  ######
data "archive_file" "ebs_volume_inventory_lambda_code" {
  type        = "zip"
  source_file = "${path.module}/lambda_code/lambda_function.py"
  output_path = "ebs_volume_inventory.zip"
}

resource "aws_lambda_function" "ebs_volume_inventory_lambda_function" {
  depends_on = [
    aws_iam_role.detached_ebs_volume_inventory_role
  ]
  function_name = "ebs-volume-inventory-lambda-${var.short_region}-${var.env}"
  role          = aws_iam_role.detached_ebs_volume_inventory_role.arn

  description = "Lambda function to scan, document, and clean up detached ebs volumes."
  environment {
    variables = {
      ENV                = var.env,
      SNS_ARN            = var.sns_topic_arn,
      ACTIVE_REGIONS     = var.active_regions,
      CROSS_ACCOUNT_ROLE = var.cross_account_inventory_role_name,
      ACCOUNT_TABLE      = var.account_table_name,
      EBS_VOLUME_TABLE   = aws_dynamodb_table.detached_ebs_volumes_inventory_table.id,
    }
  }

  handler     = "lambda_function.lambda_handler"
  memory_size = 512
  runtime     = "python3.13"

  filename         = data.archive_file.ebs_volume_inventory_lambda_code.output_path
  source_code_hash = data.archive_file.ebs_volume_inventory_lambda_code.output_base64sha256

  tags = merge(
    var.tags,
    { Name = "ebs-volume-inventory-lambda-function" }
  )
  timeout = 900

}

resource "aws_cloudwatch_log_group" "ebs_volume_inventory_lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.ebs_volume_inventory_lambda_function.function_name}"
  retention_in_days = 30
}

resource "aws_lambda_function_event_invoke_config" "ebs_volume_inventory_lambda_failure_event" {
  function_name          = aws_lambda_function.ebs_volume_inventory_lambda_function.function_name
  maximum_retry_attempts = 0

  destination_config {
    on_failure {
      destination = var.sns_topic_arn
    }
  }
}