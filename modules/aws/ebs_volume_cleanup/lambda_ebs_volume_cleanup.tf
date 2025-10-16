
# ######  EBS Cleanup Lambda  ######
data "archive_file" "ebs_volume_cleanup_lambda_code" {
  type        = "zip"
  source_file = "${path.module}/lambda_code/lambda_function.py"
  output_path = "ebs_volume_cleanup.zip"
}

resource "aws_lambda_function" "ebs_volume_cleanup_lambda_function" {
  depends_on = [
    aws_iam_role.ebs_volume_cleanup_role
  ]
  function_name = "ebs-volume-cleanup-lambda-${var.short_region}-${var.env}"
  role          = aws_iam_role.ebs_volume_cleanup_role.arn

  description = "Lambda function to scan, document, and clean up detached ebs volumes."
  environment {
    variables = {
      ENV                   = var.env,
      SNS_ARN               = var.sns_topic_arn,
      CROSS_ACCOUNT_ROLE    = var.cross_account_cleanup_role_name,
      ACCOUNT_TABLE         = var.account_table_name,
      EBS_VOLUME_TABLE      = var.ebs_volume_table_name,
      CLEANUP_SAVINGS_TABLE = var.cleanup_savings_table_name,
    }
  }

  handler     = "lambda_function.lambda_handler"
  memory_size = 256
  runtime     = "python3.13"

  filename         = data.archive_file.ebs_volume_cleanup_lambda_code.output_path
  source_code_hash = data.archive_file.ebs_volume_cleanup_lambda_code.output_base64sha256

  tags = merge(
    var.tags,
    { Name = "ebs-volume-cleanup-lambda-function" }
  )
  timeout = 900
  vpc_config {
    security_group_ids = [var.lambda_security_group_id]
    subnet_ids         = var.subnet_ids
  }
}

resource "aws_cloudwatch_log_group" "ebs_volume_cleanup_lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.ebs_volume_cleanup_lambda_function.function_name}"
  retention_in_days = 30
}

resource "aws_lambda_function_event_invoke_config" "ebs_volume_cleanup_lambda_failure_event" {
  function_name          = aws_lambda_function.ebs_volume_cleanup_lambda_function.function_name
  maximum_retry_attempts = 0

  destination_config {
    on_failure {
      destination = var.sns_topic_arn
    }
  }
}