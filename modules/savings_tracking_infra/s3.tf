resource "aws_s3_bucket" "account_storage_bucket" {
  bucket        = "idp-cost-management-${var.short_region}-${var.env}-${var.account_id}"

  tags = var.tags
}

resource "aws_s3_bucket_public_access_block" "account_storage_public_block" {
  bucket = aws_s3_bucket.account_storage_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}