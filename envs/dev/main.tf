
module "core_infrastructure" {
  source = "../../modules/core_infra"

  sns_contact_email = var.sns_contact_email
  env               = var.env
  vpc_id            = var.vpc_id
  tags = merge(
    var.tags,
    {
      module = "aws/core_infrastructure"
    }
  )
}

module "single_account_mode" {
  count  = var.multi_account_mode ? 0 : 1
  source = "../../modules/single_account_mode"

  dynamodb_accounts_table_name     = module.core_infrastructure.account_table_name
  dynamodb_accounts_table_hash_key = module.core_infrastructure.account_table_hash_key
  env                              = var.env
  target_account_id                = local.deployment_account_id
  target_account_name              = "dev-account"
}

module "multi_account_mode" {
  count  = var.multi_account_mode ? 1 : 0
  source = "../../modules/multi_account_mode"

  dynamodb_accounts_table_name = module.core_infrastructure.account_table_name
  dynamodb_accounts_table_arn  = module.core_infrastructure.account_table_arn
  env                          = var.env
  inactive_accounts_list       = var.inactive_accounts_list
  lambda_security_group_id     = module.core_infrastructure.lambda_security_group_id
  management_account_role_arn  = var.management_account_role_arn
  short_region                 = local.short_region
  sns_topic_arn                = module.core_infrastructure.idp_automation_sns_topic
  subnet_ids                   = var.subnet_ids
  tags = merge(
    var.tags,
    {
      module = "aws/multi_account_mode"
    }
  )
}

module "savings_tracking_infrastructure" {
  source = "../../modules/savings_tracking_infra"

  account_id   = local.deployment_account_id
  env          = var.env
  short_region = local.short_region
  tags = merge(
    var.tags,
    {
      module = "aws/savings_tracking"
    }
  )
}

module "ami_inventory" {
  source = "../../modules/aws/ami_inventory"

  account_table_name                = module.core_infrastructure.account_table_name
  account_table_arn                 = module.core_infrastructure.account_table_arn
  active_regions                    = var.active_regions
  cross_account_inventory_role_name = var.cross_account_inventory_role_name
  env                               = var.env
  short_region                      = local.short_region
  sns_topic_arn                     = module.core_infrastructure.idp_automation_sns_topic
  lambda_security_group_id          = module.core_infrastructure.lambda_security_group_id
  subnet_ids                        = var.subnet_ids
  tags = merge(
    var.tags,
    {
      module = "aws/ami_inventory"
    }
  )
}

module "ami_cleanup" {
  source = "../../modules/aws/ami_cleanup"

  account_table_name              = module.core_infrastructure.account_table_name
  account_table_arn               = module.core_infrastructure.account_table_arn
  ami_table_name                  = module.ami_inventory.ami_inventory_table_name
  ami_table_arn                   = module.ami_inventory.ami_inventory_table_arn
  cleanup_savings_table_arn       = module.savings_tracking_infrastructure.resource_cleanup_savings_table_arn
  cleanup_savings_table_name      = module.savings_tracking_infrastructure.resource_cleanup_savings_table_name
  cross_account_cleanup_role_name = var.cross_account_cleanup_role_name
  env                             = var.env
  lambda_security_group_id        = module.core_infrastructure.lambda_security_group_id
  short_region                    = local.short_region
  sns_topic_arn                   = module.core_infrastructure.idp_automation_sns_topic
  subnet_ids                      = var.subnet_ids
  tags = merge(
    var.tags,
    {
      module = "aws/ami_cleanup"
    }
  )
}

module "ebs_snapshot_inventory" {
  source = "../../modules/aws/ebs_snapshot_inventory"

  account_table_name                = module.core_infrastructure.account_table_name
  account_table_arn                 = module.core_infrastructure.account_table_arn
  active_regions                    = var.active_regions
  cross_account_inventory_role_name = var.cross_account_inventory_role_name
  env                               = var.env
  short_region                      = local.short_region
  sns_topic_arn                     = module.core_infrastructure.idp_automation_sns_topic
  lambda_security_group_id          = module.core_infrastructure.lambda_security_group_id
  subnet_ids                        = var.subnet_ids
  tags = merge(
    var.tags,
    {
      module = "aws/ebs_snapshot_inventory"
    }
  )
}

module "ebs_snapshot_cleanup" {
  source = "../../modules/aws/ebs_snapshot_cleanup"

  account_table_name              = module.core_infrastructure.account_table_name
  account_table_arn               = module.core_infrastructure.account_table_arn
  ebs_snapshot_table_name         = module.ebs_snapshot_inventory.ebs_snapshot_dynamodb_table_name
  ebs_snapshot_table_arn          = module.ebs_snapshot_inventory.ebs_snapshot_dynamodb_table_arn
  cleanup_savings_table_arn       = module.savings_tracking_infrastructure.resource_cleanup_savings_table_arn
  cleanup_savings_table_name      = module.savings_tracking_infrastructure.resource_cleanup_savings_table_name
  cross_account_cleanup_role_name = var.cross_account_cleanup_role_name
  env                             = var.env
  lambda_security_group_id        = module.core_infrastructure.lambda_security_group_id
  short_region                    = local.short_region
  sns_topic_arn                   = module.core_infrastructure.idp_automation_sns_topic
  subnet_ids                      = var.subnet_ids
  tags = merge(
    var.tags,
    {
      module = "aws/ebs_snapshot_cleanup"
    }
  )
}

module "ebs_volume_inventory" {
  source = "../../modules/aws/ebs_volume_inventory"

  account_table_name                = module.core_infrastructure.account_table_name
  account_table_arn                 = module.core_infrastructure.account_table_arn
  active_regions                    = var.active_regions
  cross_account_inventory_role_name = var.cross_account_inventory_role_name
  env                               = var.env
  short_region                      = local.short_region
  sns_topic_arn                     = module.core_infrastructure.idp_automation_sns_topic
  tags = merge(
    var.tags,
    {
      module = "aws/ebs_volume_inventory"
    }
  )
}

module "ebs_volume_cleanup" {
  source = "../../modules/aws/ebs_volume_cleanup"

  account_table_name              = module.core_infrastructure.account_table_name
  account_table_arn               = module.core_infrastructure.account_table_arn
  ebs_volume_table_name           = module.ebs_volume_inventory.detached_ebs_volume_inventory_table_name
  ebs_volume_table_arn            = module.ebs_volume_inventory.detached_ebs_volume_inventory_table_arn
  cleanup_savings_table_arn       = module.savings_tracking_infrastructure.resource_cleanup_savings_table_arn
  cleanup_savings_table_name      = module.savings_tracking_infrastructure.resource_cleanup_savings_table_name
  cross_account_cleanup_role_name = var.cross_account_cleanup_role_name
  env                             = var.env
  lambda_security_group_id        = module.core_infrastructure.lambda_security_group_id
  short_region                    = local.short_region
  sns_topic_arn                   = module.core_infrastructure.idp_automation_sns_topic
  subnet_ids                      = var.subnet_ids
  tags = merge(
    var.tags,
    {
      module = "aws/ebs_volume_cleanup"
    }
  )
}

module "savings_reports" {
  source = "../../modules/aws/savings_reports"

  ebs_volume_table_arn        = module.ebs_volume_inventory.detached_ebs_volume_inventory_table_arn
  ebs_volume_table_name       = module.ebs_volume_inventory.detached_ebs_volume_inventory_table_name
  ebs_snapshot_table_arn      = module.ebs_snapshot_inventory.ebs_snapshot_dynamodb_table_arn
  ebs_snapshot_table_name     = module.ebs_snapshot_inventory.ebs_snapshot_dynamodb_table_name
  env                         = var.env
  lambda_security_group_id    = module.core_infrastructure.lambda_security_group_id
  resource_savings_table_arn  = module.savings_tracking_infrastructure.resource_cleanup_savings_table_arn
  resource_savings_table_name = module.savings_tracking_infrastructure.resource_cleanup_savings_table_name
  s3_storage_bucket_arn       = module.savings_tracking_infrastructure.s3_storage_bucket_arn
  s3_storage_bucket_name      = module.savings_tracking_infrastructure.s3_storage_bucket_name
  short_region                = local.short_region
  sns_topic_arn               = module.core_infrastructure.idp_automation_sns_topic
  subnet_ids                  = var.subnet_ids
  tags = merge(
    var.tags,
    {
      module = "aws/savings_reports"
    }
  )
}

module "http_requests_python313" {
  source = "../../modules/http_requests"
}
