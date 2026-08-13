resource "aws_s3_bucket" "dvc" {
  bucket = var.dvc_bucket_name
  lifecycle { prevent_destroy = true }
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
  }
}
