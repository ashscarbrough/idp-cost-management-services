# ### AWS Account Pull Lambda ###
resource "aws_iam_role" "account_list_processing_lambda_role" {
  name = "account-list-processing-lambda-role"
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

resource "aws_iam_policy" "account_list_processing_lambda_policy" {
  name = "account-list-processing-lambda-policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
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
        Sid    = "AssumeOrganizationAccountRole"
        Effect = "Allow",
        Action = [
          "sts:AssumeRole"
        ],
        Resource = [
          var.management_account_role_arn
        ]
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
          "dynamodb:PutItem"
        ]
        Resource = [var.dynamodb_accounts_table_arn]
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
        ]
        Resource = ["arn:aws:secretsmanager:*:*:secret:*"]
      },
      {
        Sid    = "AssumeManagementAccountRole"
        Effect = "Allow",
        Action = [
          "sts:AssumeRole"
        ],
        Resource = [
          var.management_account_role_arn
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

resource "aws_iam_role_policy_attachment" "account_list_processing_role_policy_attachment" {
  policy_arn = aws_iam_policy.account_list_processing_lambda_policy.arn
  role       = aws_iam_role.account_list_processing_lambda_role.name
}
