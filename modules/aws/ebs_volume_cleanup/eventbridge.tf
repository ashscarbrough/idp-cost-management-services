
###  EVENTBRIDGE EBS VOLUME CLEANUP RULE CONFIGURATION  ###
resource "aws_cloudwatch_event_rule" "ebs_volume_cleanup_lambda_every_morning" {
  name                = "ebs-volume-cleanup-rule"
  description         = "Triggers account pull every morning"
  schedule_expression = "cron(45 6 * * ? *)"
  state               = var.env != "prod" ? "DISABLED" : "ENABLED"
}

resource "aws_cloudwatch_event_target" "trigger_ebs_volume_cleanup_lambda_on_schedule" {
  rule      = aws_cloudwatch_event_rule.ebs_volume_cleanup_lambda_every_morning.name
  target_id = "lambda"
  arn       = aws_lambda_function.ebs_volume_cleanup_lambda_function.arn
}

resource "aws_lambda_permission" "allow_eventbridge_to_call_ebs_volume_cleanup_lambda" {
  statement_id  = "AllowEBSVolumeCleanupExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ebs_volume_cleanup_lambda_function.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ebs_volume_cleanup_lambda_every_morning.arn
}
