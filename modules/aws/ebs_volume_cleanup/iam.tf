# ### Master Automation Cloud resources management role ###
resource "aws_iam_role" "ebs_volume_cleanup_role" {
  name = "ebs-volume-cleanup-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_policy" "ebs_volume_cleanup_policy" {
  name = "ebs-volume-cleanup-policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AWSLambdaVPCAccessExecutionPermissions",
        Effect = "Allow",
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DescribeSubnets",
          "ec2:DeleteNetworkInterface",
          "ec2:AssignPrivateIpAddresses",
          "ec2:UnassignPrivateIpAddresses"
        ],
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:BatchGetItem",
          "dynamodb:DescribeTable",
          "dynamodb:ListTables",
          "dynamodb:ListGlobalTables",
          "dynamodb:GetItem",
          "dynamodb:GetResourcePolicy",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:UpdateItem",
          "dynamodb:PutItem",
          "dynamodb:DeleteItem"
        ]
        Resource = [
          var.account_table_arn,
          var.ebs_volume_table_arn,
          var.cleanup_savings_table_arn
        ]
      },
      {
        Sid    = "ResourceCleanupPermissions"
        Effect = "Allow",
        Action = [
          "ec2:DeleteVolume"
        ],
        Resource = [
          "*"
        ]
      },
      {
        Sid    = "DenyResourceCleanupWithoutTag"
        Effect = "Deny",
        Action = [
          "ec2:DeleteVolume"
        ],
        Resource = [
          "*"
        ],
        Condition = {
          Null = {
            "aws:RequestTag/identified_for_deletion" : "true"
          }
        }
      },
      {
        Sid    = "AssumeRolePermissions"
        Effect = "Allow",
        Action = [
          "sts:AssumeRole"
        ],
        Resource = [
          "arn:aws:iam::*:role/${var.cross_account_cleanup_role_name}"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "sns:publish"
        ]
        Resource = [var.sns_topic_arn]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ebs_volume_cleanup_role_policy_attachment" {
  policy_arn = aws_iam_policy.ebs_volume_cleanup_policy.arn
  role       = aws_iam_role.ebs_volume_cleanup_role.name
}

resource "aws_iam_role_policy_attachment" "ebs_volume_cleanup_read_policy_attachment" {
  role       = aws_iam_role.ebs_volume_cleanup_role.name
  policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess"
}
