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

variable "artifact_bucket_name" {
  type        = string
  description = "Globally unique private bucket for MLflow artifacts and campaign outputs."
}

variable "dvc_dataset_s3_uri" {
  type        = string
  description = "Exact S3 URI for the DVC-versioned CSV object used by the campaign."
  validation {
    condition     = can(regex("^s3://[^/]+/.+$", var.dvc_dataset_s3_uri))
    error_message = "dvc_dataset_s3_uri must be a complete s3:// URI."
  }
}

variable "dvc_data_version" {
  type        = string
  description = "Content hash from data/raw/online_shoppers_intention.csv.dvc."
}

variable "repository_url" {
  type        = string
  description = "Public Git repository cloned by the EC2 experiment runner."
}

variable "git_ref" {
  type        = string
  description = "Branch or tag containing the exact experiment implementation."
}

variable "allowed_cidr" {
  type        = string
  description = "Single trusted CIDR allowed to access the MLflow UI on port 5000."
  validation {
    condition     = can(cidrnetmask(var.allowed_cidr))
    error_message = "allowed_cidr must be a valid IPv4 CIDR."
  }
}

variable "instance_type" {
  type    = string
  default = "t3.xlarge"
}

variable "instance_profile_name" {
  type        = string
  description = "Existing EC2 instance profile with S3 and SSM access."
  default     = "LabInstanceProfile"
}

variable "subnet_id" {
  type        = string
  description = "Optional public subnet. The first default subnet is used when null."
  default     = null
  nullable    = true
}

variable "root_volume_gb" {
  type    = number
  default = 60
  validation {
    condition     = var.root_volume_gb >= 30
    error_message = "root_volume_gb must be at least 30 GB for experiment dependencies."
  }
}

variable "experiment_name" {
  type    = string
  default = "online-shoppers-ec2-large-experiment"
}

variable "registered_model_name" {
  type    = string
  default = "online-shoppers-purchase-intention"
}
