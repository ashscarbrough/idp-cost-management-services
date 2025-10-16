# ### Master Automation Cloud resources management role ###
resource "aws_iam_role" "ebs_snapshot_inventory_role" {
  name = "ebs-snapshot-inventory-role"
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

resource "aws_iam_policy" "ebs_snapshot_inventory_policy" {
  name = "ebs-snapshot-inventory-policy"
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
          aws_dynamodb_table.ebs_snapshot_table.arn
        ]
      },
      {
        Sid    = "TagPermissions"
        Effect = "Allow",
        Action = [
          "ec2:CreateTags",
          "ec2:DeleteTags",
          "rds:AddTagsToResource",
          "rds:RemoveTagsFromResource",
          "dynamodb:TagResource",
          "dynamodb:UntagResource",
          "iam:TagPolicy",
          "iam:TagRole",
          "iam:UntagPolicy",
          "iam:UntagRole",
          "cloudfront:TagResource",
          "cloudfront:UntagResource",
          "lambda:TagResource",
          "lambda:UntagResource",
          "s3:TagResource",
          "s3:UntagResource",
          "elasticfilesystem:CreateTags",
          "elasticfilesystem:DeleteTags",
          "elasticfilesystem:TagResource",
          "elasticfilesystem:UntagResource",
          "eks:TagResource",
          "eks:UntagResource",
          "ecs:TagResource",
          "ecs:UntagResource",
          "elasticbeanstalk:AddTags",
          "elasticbeanstalk:RemoveTags",
          "elasticbeanstalk:UpdateTagsForResource",
          "fsx:TagResource",
          "fsx:UntagResource",
          "es:AddTags",
          "es:RemoveTags",
          "redshift:CreateTags",
          "redshift:DeleteTags",
          "resource-groups:Tag",
          "resource-groups:Untag",
          "sqs:TagQueue",
          "sqs:UntagQueue",
          "imagebuilder:TagResource",
          "imagebuilder:UntagResource"
        ],
        Resource = [
          "*"
        ]
      },
      {
        Sid    = "AssumeRolePermissions"
        Effect = "Allow",
        Action = [
          "sts:AssumeRole"
        ],
        Resource = [
          "arn:aws:iam::*:role/${var.cross_account_inventory_role_name}"
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

resource "aws_iam_role_policy_attachment" "ebs_snapshot_inventory_role_policy_attachment" {
  policy_arn = aws_iam_policy.ebs_snapshot_inventory_policy.arn
  role       = aws_iam_role.ebs_snapshot_inventory_role.name
}

resource "aws_iam_role_policy_attachment" "ebs_snapshot_inventory_read_policy_attachment" {
  role       = aws_iam_role.ebs_snapshot_inventory_role.name
  policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess"
}
