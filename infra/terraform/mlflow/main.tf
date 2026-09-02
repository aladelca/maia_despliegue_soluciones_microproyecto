data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  filter {
    name   = "default-for-az"
    values = ["true"]
  }
}

data "aws_ssm_parameter" "al2023_ami" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

resource "aws_security_group" "mlflow" {
  name_prefix = "${var.project_name}-${var.environment}-mlflow-"
  description = "Restrict MLflow UI and API to the trusted course client CIDR."
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "MLflow UI and tracking API"
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  lifecycle { create_before_destroy = true }
}

resource "aws_instance" "mlflow_experiment" {
  ami                         = data.aws_ssm_parameter.al2023_ami.value
  instance_type               = var.instance_type
  subnet_id                   = coalesce(var.subnet_id, sort(data.aws_subnets.default.ids)[0])
  associate_public_ip_address = true
  iam_instance_profile        = var.instance_profile_name
  vpc_security_group_ids      = [aws_security_group.mlflow.id]

  user_data_replace_on_change = true
  user_data = templatefile("${path.module}/user_data.sh.tftpl", {
    artifact_bucket_name  = aws_s3_bucket.mlflow.id
    aws_region            = var.aws_region
    dvc_data_version      = var.dvc_data_version
    dvc_dataset_s3_uri    = var.dvc_dataset_s3_uri
    experiment_name       = var.experiment_name
    git_ref               = var.git_ref
    registered_model_name = var.registered_model_name
    repository_url        = var.repository_url
  })

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
  }

  root_block_device {
    encrypted             = true
    volume_size           = var.root_volume_gb
    volume_type           = "gp3"
    delete_on_termination = false
  }

  tags = {
    Name    = "${var.project_name}-${var.environment}-mlflow-experiment"
    Purpose = "MLflow tracking and bounded model experimentation"
  }

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [
    aws_s3_bucket_policy.mlflow_enforce_tls,
    aws_s3_bucket_public_access_block.mlflow,
  ]
}
