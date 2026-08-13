output "state_bucket_name" {
  description = "Bucket used by the foundation and service partial backends."
  value       = aws_s3_bucket.terraform_state.id
}
