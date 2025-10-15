# idp-cost-management-services
Supporting resources set up in a serverless architecture to track resource costs, provide cloud service observability, and remove unneeded assets.  This data is stored in DynamoDB tables as a fast and simple persistent store and reports can be created and stored an S3 bucket or can integrate with API for an IDP.

# General Overview
Root holds repo tooling and a “reference” versions.tf/providers.tf.
Modules are versionable and reusable (even by others).
envs/ isolates dev/prod (directory-per-env is clearer for interviews than workspaces).
GitHub Actions provides guardrails (fmt, validate, lint, plan).


# Project Structure
```
idp-cost-management-services/
├── modules/         # Reusable Terraform modules
├── envs/            # Environment-specific configurations (dev/prod)
├── .github/         # GitHub Actions workflows
├── reference/       # Reference Terraform files (versions.tf, providers.tf)
└── README.md        # Project documentation
```

# Solution Overview

This solution can be deployed in two configurations:
- Single Account
- Multi Account

## Single Account

![Single Account Architecture](./docs/images/cost_management_single_account.jpg)

The solution and its resources are deployed to a **single account** that hosts the compute and data infrastructure required for inventory and cleanup of cloud services.  This is ideal for a development environment, or for simple testing of the solution outputs.

### Key Operations

- **Resource Inventory**
  - Runs on a schedule.
  - Uses *Inventory Lambda Functions* to assume the `cross_account_inventory_role` in the current account.
  - Updates the status, configuration, and tags of AWS resources (e.g., AMIs, EBS snapshots, EBS volumes).

- **Resource Cleanup**
  - Runs on a schedule.
  - Uses *Cleanup Lambda Functions* to assume the `cross_account_cleanup_role` in the current account.
  - Removes AWS resources marked for deletion (with appropriate tags).

- **Savings Reports**
  - Runs on a schedule.
  - Generates savings reports and stores them in S3 for business analysts to review.

Each operation is automated and leverages the least-privilege IAM roles for secure access and management.

## Multi Account

![Multi Account Architecture](./docs/images/cost_management_multi_account.jpg)

The solution and its resources are deployed to a **tooling account** that hosts the compute and data infrastructure required for inventory and cleanup of cloud services.

### Key Operations

- **Account Inventory (Account Pull)**
  - Runs on a schedule.
  - Uses the *Account Pull Lambda* to assume a role in the Management Account and update the status/configuration of AWS accounts.

- **Resource Inventory**
  - Runs on a schedule.
  - Uses *Inventory Lambda Functions* to assume the `cross_account_inventory_roles` in each account.
  - Updates the status, configuration, and tags of AWS resources (e.g., AMIs, EBS snapshots, EBS volumes).

- **Resource Cleanup**
  - Runs on a schedule.
  - Uses *Cleanup Lambda Functions* to assume the `cross_account_cleanup_roles` in each account.
  - Removes AWS resources marked for deletion (with appropriate tags).

- **Savings Reports**
  - Runs on a schedule.
  - Generates savings reports and stores them in S3 for business analysts to review.

Each operation is automated and leverages cross-account IAM roles for secure access and management.

# Usage

## Preparing Your AWS Account/Organization for the Solution

### Required IAM Roles

This solution requires multiple IAM roles to enable resource discovery and cleanup across your AWS organization. These roles and policies are deployed outside of this solution, allowing your organization to maintain control over IAM resources. Revoking these roles, policies, or associated trust relationships will prevent this solution from authenticating with organization accounts.

### Role Types

1. **Management Account/Organization Role**
    - Enables the `account_pull` Lambda module to access organization accounts.
    - Automatically inventories new accounts and removes old accounts connected to the organization.

2. **Inventory Role**
    - Must be deployed to all accounts within the organization (using Terraform, CloudFormation StackSet, etc.).
    - Used by inventory modules to:
        - Discover cloud resources.
        - Store resource data.
        - Tag resources for deletion based on established criteria.

3. **Cleanup Role**
    - Must be deployed to all accounts within the organization (using Terraform, CloudFormation StackSet, etc.).
    - Used by cleanup modules to:
        - Review resource data.
        - Clean up resources tagged for deletion.

> **Note:** Deploy these roles using your organization's preferred method. Ensure trust relationships and permissions are correctly configured for seamless operation.

### Managment Account/Organization Role

Deploy the following role to your management account (replace the role inputs for <tooling-account-id>: which is the account this solution is deployed, and the <role-name>: found in the module aws_iam_role.account_list_processing_lambda_role).  The role name is *"account-list-processing-lambda-role"* by default.

```hcl
resource "aws_iam_role" "organization_account_inventory_role" {
  name = "organization-account-inventory-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        AWS = "arn:aws:iam::<tooling-account-id>:role/<role-name>"
      }
    }]
  })
}

resource "aws_iam_policy" "organization_account_inventory_lambda_policy" {
  name = "organization-account-inventory-policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
        {
            Effect = "Allow"
            Action = [
                "organizations:ListAccounts",
                "organizations:ListTagsForResource",
                "organziations:ListParents"
        
            ]
            Resource = "*"
        }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "organization_account_inventory_role_policy_attachment" {
  policy_arn = aws_iam_policy.organization_account_inventory_lambda_policy.arn
  role       = aws_iam_role.organization_account_inventory_role.name
}

```

The name of this role will need to be provided as a variable in your variables: **management_account_role_arn**

### Inventory Role

Deploy the following role to your management account (replace the role inputs for <tooling-account-id>: which is the account this solution is deployed, and the <role-name>: found in the module aws_iam_role.account_list_processing_lambda_role).  The role name is postfixed with *"\*-inventory-role"*, though a wildcard can be used, it is advisable to add each inventory role individually to your trust as a list.

**Single-Account Inventory Role**
```hcl
resource "aws_iam_role" "cross_account_inventory_role" {
  name = "single-account-inventory-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        AWS = [
          "arn:aws:iam::<target-account-id>:root"
        ]
      }
    }]
  })
}
```

**Multi-Account Cross-Account Inventory Role**
```hcl
resource "aws_iam_role" "cross_account_inventory_role" {
  name = "cross-account-inventory-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        AWS = [
          "arn:aws:iam::<tooling-account-id>:role/ebs-volume-inventory-role",
          "arn:aws:iam::<tooling-account-id>:role/ami-inventory-role",
          "arn:aws:iam::<tooling-account-id>:role/ebs-snapshot-inventory-role",
          "arn:aws:iam::<tooling-account-id>:role/detached-ebs-volume-inventory-role",
          ...
        ]
      }
    }]
  })
}
```

**Inventory Role Policy and Attachment**
```hcl
resource "aws_iam_policy" "cross_account_inventory_policy" {
  name = "cross-account-inventory-policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "TagPermissions"
        Effect = "Allow",
        Action = [
          "ec2:DescribeImages",
          "ec2:DescribeSnapshots",
          "ec2:DescribeVolumes",
          "ec2:CreateTags",
          "ec2:DeleteTags"
        ],
        Resource = [
          "*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "cross_account_inventory_role_policy_attachment" {
  policy_arn = aws_iam_policy.cross_account_inventory_policy.arn
  role       = aws_iam_role.cross_account_inventory_role.name
}

resource "aws_iam_role_policy_attachment" "cross_account_inventory_read_policy_attachment" {
  role       = aws_iam_role.cross_account_inventory_role.name
  policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess"
}

```

The name of this role will need to be provided as a variable in your variables: **cross_account_inventory_role_name**


### Cleanup Role

Deploy the following role to your management account (replace the role inputs for <tooling-account-id>: which is the account this solution is deployed, and the <role-name>: found in the module aws_iam_role.account_list_processing_lambda_role).  The role name is postfixed with *"\*-cleanup-role"*, though a wildcard can be used, it is advisable to add each inventory role individually to your trust as a list.


**Single-Account Inventory Role**
```hcl
resource "aws_iam_role" "cross_account_inventory_role" {
  name = "single-account-cleanup-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        AWS = [
          "arn:aws:iam::<target-account-id>:root"
        ]
      }
    }]
  })
}
```

**Multi-Account Cross-Account Inventory Role**
```hcl
resource "aws_iam_role" "ebs_snapshot_cleanup_role" {
  name = "cross-account-cleanup-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        AWS = [
          "arn:aws:iam::<tooling-account-id>:role/ebs-volume-cleanup-role",
          "arn:aws:iam::<tooling-account-id>:role/ami-cleanup-role",
          "arn:aws:iam::<tooling-account-id>:role/ebs-snapshot-inventory-role",
          "arn:aws:iam::<tooling-account-id>:role/detached-ebs-volume-inventory-role",
          ...
        ]
      }
    }]
  })
}
```

**Inventory Role Policy and Attachment**
```hcl
resource "aws_iam_policy" "cross_account_cleanup_policy" {
  name = "cross-account-cleanup-policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ResourceCleanupPermissions"
        Effect = "Allow",
        Action = [
          "ec2:DeleteVolume", 
          "ec2:DeleteSnapshot", 
          "ec2:DeregisterImage"
        ],
        Resource = [
          "*"
        ]
      },
      {
        Sid    = "DenyResourceCleanupWithoutTag"
        Effect = "Deny",
        Action = [
          "ec2:DeleteVolume", 
          "ec2:DeleteSnapshot", 
          "ec2:DeregisterImage"
        ],
        Resource = [
          "*"
        ],
        Condition = {
          Null = {
            "aws:RequestTag/identified_for_deletion" : "true"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "cross_account_cleanup_role_policy_attachment" {
  policy_arn = aws_iam_policy.cross_account_cleanup_policy.arn
  role       = aws_iam_role.cross_account_cleanup_role.name
}

resource "aws_iam_role_policy_attachment" "cross_account_cleanup_read_policy_attachment" {
  role       = aws_iam_role.cross_account_cleanup_role.name
  policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess"
}
```

The name of this role will need to be provided as a variable in your variables: **cross_account_cleanup_role_name**


## Github Actions Deployment

The `.github/workflows/terraform-validate-apply.yaml` file defines a GitHub Actions workflow that automates Terraform tasks for your project.

### How It Works

- **Trigger:**  
    The workflow runs on events such as pushes or pull requests to specific branches (e.g., `main` or `dev`).

- **Setup:**  
    - Checks out your code.
    - Sets up the Terraform CLI.
    - Optionally configures cloud provider credentials using GitHub secrets.

- **Validation Steps:**  
    - Runs `terraform fmt` to check code formatting.
    - Runs `terraform validate` to ensure configuration is syntactically correct.
    - May run `terraform lint` for style and best practices.

- **Planning:**  
    - Executes `terraform plan` to preview infrastructure changes.

- **Apply (Deployment):**  
    - Runs `terraform apply` to deploy resources if the plan is approved.

Refer to the workflow file for customization and additional steps.

## Local Deployment
1. Clone the repository:
    ```bash
    git clone https://github.com/your-org/idp-cost-management-services.git
    ```
2. Configure environment variables and provider credentials.
3. Deploy resources for your environment:
    ```bash
    cd envs/dev
    terraform init
    terraform plan
    terraform apply
    ```
4. Review cost and observability data in the configured S3 bucket or via the API.

# Troubleshooting
- **Terraform errors:** Run `terraform fmt` and `terraform validate` to check for syntax issues.
- **Missing credentials:** Ensure your cloud provider credentials are set in your environment.
- **GitHub Actions failures:** Review workflow logs for details and verify configuration files.

# Future Features
- Update Lambda functions to use aioboto3 for asynchronous aws api calls.
- Integration with additional cloud providers and cloud tools.
    - Azure
    - GCP
    - HCP
- Add Cloud Reasource inventory and cleanup capabilities
    - EC2 Instances
    - RDS
    - DynamoDB
    - IAM
    - CloudFront
    - Lambda
    - S3
    - EFS
    - EKS
    - ECS
    - FSX
    - ElasticSearch
    - Redshift
    - SQS
    - ImageBuilder
    - Trusted Advisor Recommendations
- Add priority Trusted Advisor recommendations to a searchable inventory.
    - Build automations to build stories/notification for priority items.
- Incremental efforts toward least privilege IAM policies.
- Support for custom notification channels.
- Enable S3 as persistent storage of inventory data.
- Add Config Rule triggers in Management Account to dynamically update Accounts Table when organization events are matched.