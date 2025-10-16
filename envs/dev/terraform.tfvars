## Terraform variables for the dev environment
active_regions                    = "us-east-1, us-east-2, us-west-1, us-west-2"
aws_region                        = "us-east-1"
cross_account_inventory_role_name = "cross-account-inventory-role"
cross_account_cleanup_role_name   = "cross-account-cleanup-role"
env                               = "dev"
inactive_accounts_list            = ""
management_account_role_arn       = ""
multi_account_mode                = false
sns_contact_email                 = "ash.scarbrough@gmail.com"
subnet_ids                        = ["subnet-381ecc64", "subnet-3551c83a"]
tags                              = { repository = "github.com/ashscarbrough/idp-cost-management-services" }
vpc_id                            = "vpc-dd4059a6"
