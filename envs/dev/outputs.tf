
output "platform_automation_sns_topic" {
  description = "SNS topic for notications regarding Platform Automation solution"
  value       = module.core_infrastructure.idp_automation_sns_topic
}
