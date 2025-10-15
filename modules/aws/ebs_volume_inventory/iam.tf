# ### Master Automation Cloud resources management role ###
resource "aws_iam_role" "detached_ebs_volume_inventory_role" {
  name = "detached-ebs-volume-inventory-role"
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

resource "aws_iam_policy" "detached_ebs_volume_inventory_policy" {
  name = "detached-ebs-volume-inventory-policy"
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
          aws_dynamodb_table.detached_ebs_volumes_inventory_table.arn
        ]
      },
      {
        Sid    = "TagPermissions"
        Effect = "Allow",
        Action = [
          "ec2:CreateTags",
          "ec2:DeleteTags",
          "ec2:DescribeVolumes",
          "ec2:DescribeTags"
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

resource "aws_iam_role_policy_attachment" "detached_ebs_volume_inventory_role_policy_attachment" {
  policy_arn = aws_iam_policy.detached_ebs_volume_inventory_policy.arn
  role       = aws_iam_role.detached_ebs_volume_inventory_role.name
}

resource "aws_iam_role_policy_attachment" "detached_ebs_volume_inventory_read_policy_attachment" {
  role       = aws_iam_role.detached_ebs_volume_inventory_role.name
  policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess"
}
