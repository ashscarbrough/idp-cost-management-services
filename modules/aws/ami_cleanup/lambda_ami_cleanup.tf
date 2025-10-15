
# ######  AMI Cleanup Lambda  ######
data "archive_file" "ami_cleanup_lambda_code" {
  type        = "zip"
  source_file = "${path.module}/lambda_code/lambda_function.py"
  output_path = "ami_cleanup.zip"
}

resource "aws_lambda_function" "ami_cleanup_lambda_function" {
  depends_on = [
    aws_iam_role.ami_cleanup_role
  ]
  function_name = "ami-cleanup-lambda-${var.short_region}-${var.env}"
  role          = aws_iam_role.ami_cleanup_role.arn

  description = "Lambda function to clean up amis."
  environment {
    variables = {
      ENV     = var.env,
      SNS_ARN = var.sns_topic_arn,
      CROSS_ACCOUNT_ROLE = var.cross_account_cleanup_role_name,
      ACCOUNT_TABLE = var.account_table_name,
      AMI_TABLE  = var.ami_table_name,
      CLEANUP_SAVINGS_TABLE = var.cleanup_savings_table_name
    }
  }

  handler = "lambda_function.lambda_handler"
  memory_size = 256
  runtime     = "python3.13"

  filename         = data.archive_file.ami_cleanup_lambda_code.output_path
  source_code_hash = data.archive_file.ami_cleanup_lambda_code.output_base64sha256

  tags = merge(
    var.tags,
    { Name = "ami-cleanup-lambda-function" }
  )
  timeout = 900
  vpc_config {
    security_group_ids = [var.lambda_security_group_id]
    subnet_ids         = var.subnet_ids
  }
}

resource "aws_cloudwatch_log_group" "ami_cleanup_lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.ami_cleanup_lambda_function.function_name}"
  retention_in_days = 30
}

resource "aws_lambda_function_event_invoke_config" "ami_cleanup_lambda_failure_event" {
  function_name          = aws_lambda_function.ami_cleanup_lambda_function.function_name
  maximum_retry_attempts = 0

  destination_config {
    on_failure {
      destination = var.sns_topic_arn
    }
  }
}
