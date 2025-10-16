###  EVENTBRIDGE COST SAVINGS PRINT OUT RULE CONFIGURATION  ###
resource "aws_cloudwatch_event_rule" "cost_savings_total_lambda_every_morning" {
  name                = "cost-savings-printout-rule"
  description         = "Triggers account pull every morning"
  schedule_expression = "cron(0 10 * * ? *)"
  state               = var.env != "prod" ? "DISABLED" : "ENABLED"
}

resource "aws_cloudwatch_event_target" "trigger_cost_savings_total_lambda_on_schedule" {
  rule      = aws_cloudwatch_event_rule.cost_savings_total_lambda_every_morning.name
  target_id = "lambda"
  arn       = aws_lambda_function.savings_totals_lambda_function.arn
}

resource "aws_lambda_permission" "allow_eventbridge_to_call_cost_savings_total_lambda" {
  statement_id  = "AllowCostSavingsExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.savings_totals_lambda_function.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.cost_savings_total_lambda_every_morning.arn
}

