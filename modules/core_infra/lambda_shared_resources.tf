
##### Lambda Security Groups #####
resource "aws_security_group" "idp_automation_lambda_sg" {
  name_prefix = "idp-cost-management-automation-sg"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
# trivy:ignore:AVD-AWS-0104
