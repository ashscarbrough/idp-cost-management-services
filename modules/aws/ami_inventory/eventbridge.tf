###  EVENTBRIDGE AMI INVENTORY RULE CONFIGURATION  ###
resource "aws_cloudwatch_event_rule" "ami_inventory_lambda_every_morning" {
  name                = "ami-inventory-rule"
  description         = "Triggers account pull every morning"
  schedule_expression = "cron(0 8 * * ? *)"
  state               = var.env != "prod" ? "DISABLED" : "ENABLED"
}

resource "aws_cloudwatch_event_target" "trigger_ami_inventory_lambda_on_schedule" {
  rule      = aws_cloudwatch_event_rule.ami_inventory_lambda_every_morning.name
  target_id = "lambda"
  arn       = aws_lambda_function.ami_inventory_lambda_function.arn
}

resource "aws_lambda_permission" "allow_eventbridge_to_call_ami_inventory_lambda" {
  statement_id  = "AllowAMIInvExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ami_inventory_lambda_function.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ami_inventory_lambda_every_morning.arn
}
