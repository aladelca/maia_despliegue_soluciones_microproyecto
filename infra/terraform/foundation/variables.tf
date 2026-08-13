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

variable "dvc_bucket_name" {
  type        = string
  description = "Globally unique DVC bucket name."
}

variable "terraform_state_bucket_name" {
  type        = string
  description = "Name of the bootstrap bucket used by the GitHub deployment workflow."
}

variable "github_owner" {
  type = string
}

variable "github_repository" {
  type = string
}
