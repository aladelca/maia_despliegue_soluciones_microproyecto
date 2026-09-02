resource "aws_s3_bucket" "mlflow" {
  bucket = var.artifact_bucket_name
  lifecycle { prevent_destroy = true }
}

resource "aws_s3_bucket_ownership_controls" "mlflow" {
  bucket = aws_s3_bucket.mlflow.id
  rule { object_ownership = "BucketOwnerEnforced" }
}

resource "aws_s3_bucket_versioning" "mlflow" {
  bucket = aws_s3_bucket.mlflow.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "mlflow" {
  bucket = aws_s3_bucket.mlflow.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_public_access_block" "mlflow" {
  bucket                  = aws_s3_bucket.mlflow.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "mlflow" {
  bucket     = aws_s3_bucket.mlflow.id
  depends_on = [aws_s3_bucket_versioning.mlflow]
  rule {
    id     = "abort-incomplete-uploads"
    status = "Enabled"
    filter {}
    abort_incomplete_multipart_upload { days_after_initiation = 7 }
  }
}

data "aws_iam_policy_document" "mlflow_enforce_tls" {
  statement {
    sid       = "DenyInsecureTransport"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.mlflow.arn, "${aws_s3_bucket.mlflow.arn}/*"]
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

resource "aws_s3_bucket_policy" "mlflow_enforce_tls" {
  bucket = aws_s3_bucket.mlflow.id
  policy = data.aws_iam_policy_document.mlflow_enforce_tls.json
}
