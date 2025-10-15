### Terraform HCP Role ###
resource "aws_iam_role" "terraform_workspace_inventory_role" {
  name = "terraform-workspace-role"
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

resource "aws_iam_policy" "terraform_policy" {
  name = "terraform-policy"
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
          "secretsmanager:GetSecretValue",
        ]
        Resource = ["arn:aws:secretsmanager:*:*:secret:*"]
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
        Resource = [aws_dynamodb_table.terraform_workspace_table.arn]
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

resource "aws_iam_role_policy_attachment" "terraform_role_policy_attachment" {
  policy_arn = aws_iam_policy.terraform_policy.arn
  role       = aws_iam_role.terraform_role.name
}
