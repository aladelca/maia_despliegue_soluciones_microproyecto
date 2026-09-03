variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project_name" {
  type    = string
  default = "online-shoppers-ml"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "owner" {
  type = string
}

variable "lambda_execution_role_arn" {
  type        = string
  description = "Existing Lambda execution role ARN. When null, Terraform creates a dedicated role."
  default     = null
  nullable    = true

  validation {
    condition = (
      var.lambda_execution_role_arn == null ||
      can(regex("^arn:[^:]+:iam::[0-9]{12}:role/.+$", var.lambda_execution_role_arn))
    )
    error_message = "lambda_execution_role_arn must be null or a valid IAM role ARN."
  }
}

variable "image_uri" {
  type        = string
  description = "Immutable ECR image URI including its sha256 digest."
  validation {
    condition     = can(regex("@sha256:[0-9a-f]{64}$", var.image_uri))
    error_message = "image_uri must identify an immutable ECR digest."
  }
}
variable "allowed_origin" {
  type    = string
  default = "http://localhost:3000"
}

variable "lambda_memory_mb" {
  type    = number
  default = 2048
}

variable "lambda_timeout_seconds" {
  type    = number
  default = 30
}

variable "log_retention_days" {
  type    = number
  default = 14
}
