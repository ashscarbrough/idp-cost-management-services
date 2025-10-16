
# ######  EBS Cleanup Lambda  ######
data "archive_file" "savings_totals_lambda_code" {
  type        = "zip"
  source_file = "${path.module}/lambda_code/lambda_function.py"
  output_path = "savings_totals.zip"
}

resource "aws_lambda_function" "savings_totals_lambda_function" {
  depends_on = [
    aws_iam_role.savings_totals_calculation_role
  ]
  function_name = "savings-totals-lambda-${var.short_region}-${var.env}"
  role          = aws_iam_role.savings_totals_calculation_role.arn

  description = "Lambda function to scan and document cost savings totals into CSV document."
  environment {
    variables = {
      ENV                   = var.env,
      SNS_ARN               = var.sns_topic_arn,
      EBS_VOLUME_TABLE      = var.ebs_volume_table_name,
      CLEANUP_SAVINGS_TABLE = var.resource_savings_table_name,
      EBS_SNAPSHOT_TABLE    = var.ebs_snapshot_table_name,
      S3_BUCKET             = var.s3_storage_bucket_name
    }
  }

  handler     = "lambda_function.lambda_handler"
  memory_size = 256
  runtime     = "python3.13"

  filename         = data.archive_file.savings_totals_lambda_code.output_path
  source_code_hash = data.archive_file.savings_totals_lambda_code.output_base64sha256

  tags    = var.tags
  timeout = 900

}

resource "aws_cloudwatch_log_group" "savings_totals_lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.savings_totals_lambda_function.function_name}"
  retention_in_days = 30
}

resource "aws_lambda_function_event_invoke_config" "savings_totals_lambda_failure_event" {
  function_name          = aws_lambda_function.savings_totals_lambda_function.function_name
  maximum_retry_attempts = 0

  destination_config {
    on_failure {
      destination = var.sns_topic_arn
    }
  }
}