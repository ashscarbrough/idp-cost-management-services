# ######  Account Pull Lambda  ######
data "archive_file" "aws_account_pull_lambda_code" {
  type        = "zip"
  source_file = "${path.module}/lambda_code/lambda_function.py"
  output_path = "aws_account_pull.zip"
}

resource "aws_lambda_function" "aws_account_pull" {
  depends_on = [
    aws_iam_role.account_list_processing_lambda_role,
  ]
  function_name = "aws-account-pull-${var.short_region}-${var.env}"
  role          = aws_iam_role.account_list_processing_lambda_role.arn

  description = "Lambda function to scan and store current AWS accounts pulled from Master account."
  environment {
    variables = {
      ACCOUNTS_DDB_TABLE = var.dynamodb_accounts_table_name,
      ACCOUNT_ROLE_ARN   = var.management_account_role_arn,
      ENV                = var.env,
      INACTIVE_ACCOUNTS  = var.inactive_accounts_list,
      SNS_ARN            = var.sns_topic_arn
    }
  }

  handler          = "lambda_function.lambda_handler"
  memory_size      = 128
  runtime          = "python3.13"
  filename         = data.archive_file.aws_account_pull_lambda_code.output_path
  source_code_hash = data.archive_file.aws_account_pull_lambda_code.output_base64sha256

  tags    = var.tags
  timeout = 600

}

resource "aws_cloudwatch_log_group" "account_pull_lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.aws_account_pull.function_name}"
  retention_in_days = 30
}

resource "aws_lambda_function_event_invoke_config" "account_pull_lambda_failure_event" {
  function_name          = aws_lambda_function.aws_account_pull.function_name
  maximum_retry_attempts = 0

  destination_config {
    on_failure {
      destination = var.sns_topic_arn
    }
  }
}
