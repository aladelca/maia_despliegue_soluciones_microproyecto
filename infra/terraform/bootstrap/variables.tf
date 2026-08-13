variable "aws_region" {
  type        = string
  description = "AWS region for the state bucket."
  default     = "us-east-1"
}

variable "project_name" {
  type        = string
  description = "Short project identifier."
  default     = "online-shoppers-ml"
}

variable "environment" {
  type        = string
  description = "Deployment environment."
  default     = "dev"
}

variable "owner" {
  type        = string
  description = "Owner tag used for cost attribution."
}

variable "state_bucket_name" {
  type        = string
  description = "Globally unique S3 bucket name for Terraform state."
}
