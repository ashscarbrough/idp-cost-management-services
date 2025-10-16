resource "aws_sns_topic" "idp_automation_topic" {
  name = "idp-automation-sns-${var.env}"

  kms_master_key_id = "alias/aws/sns"
}

resource "aws_sns_topic_subscription" "personal_smp_sns_subscription" {
  topic_arn = aws_sns_topic.idp_automation_topic.arn
  protocol  = "email"
  endpoint  = var.sns_contact_email
}
