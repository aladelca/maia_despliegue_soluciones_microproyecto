resource "aws_s3_bucket" "dvc" {
  bucket = var.dvc_bucket_name
  lifecycle { prevent_destroy = true }
}

resource "aws_s3_bucket_ownership_controls" "dvc" {
  bucket = aws_s3_bucket.dvc.id
  rule { object_ownership = "BucketOwnerEnforced" }
}

resource "aws_s3_bucket_versioning" "dvc" {
  bucket = aws_s3_bucket.dvc.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "dvc" {
  bucket = aws_s3_bucket.dvc.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_public_access_block" "dvc" {
  bucket                  = aws_s3_bucket.dvc.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "dvc" {
  bucket     = aws_s3_bucket.dvc.id
  depends_on = [aws_s3_bucket_versioning.dvc]
  rule {
    id     = "expire-old-noncurrent-versions"
    status = "Enabled"
    filter {}
    noncurrent_version_expiration { noncurrent_days = 90 }
    abort_incomplete_multipart_upload { days_after_initiation = 7 }
  }
}

data "aws_iam_policy_document" "dvc_enforce_tls" {
  statement {
    sid     = "DenyInsecureTransport"
    effect  = "Deny"
    actions = ["s3:*"]
    resources = [
      aws_s3_bucket.dvc.arn,
      "${aws_s3_bucket.dvc.arn}/*",
    ]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "dvc_enforce_tls" {
  bucket = aws_s3_bucket.dvc.id
  policy = data.aws_iam_policy_document.dvc_enforce_tls.json
}
