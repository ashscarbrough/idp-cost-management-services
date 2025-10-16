###  EVENTBRIDGE ACCOUNT RULE CONFIGURATION  ###
resource "aws_cloudwatch_event_rule" "aws_account_pull_lambda_every_day" {
  name                = "aws-account-pull-rule"
  description         = "Triggers account pull every day at 2AM"
  schedule_expression = "cron(0 6 * * ? *)"
  state               = var.env != "prod" ? "DISABLED" : "ENABLED"
}

resource "aws_cloudwatch_event_target" "trigger_account_pull_lambda_on_schedule" {
  rule      = aws_cloudwatch_event_rule.aws_account_pull_lambda_every_day.name
  target_id = "lambda"
  arn       = aws_lambda_function.aws_account_pull.arn
}

resource "aws_lambda_permission" "allow_eventbridge_to_call_aws_account_pull_lambda" {
  statement_id  = "AllowAccountPullExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.aws_account_pull.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.aws_account_pull_lambda_every_day.arn
}
