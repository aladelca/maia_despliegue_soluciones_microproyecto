resource "aws_ecr_repository" "api" {
  count                = var.enable_deployment_resources ? 1 : 0
  name                 = "${var.project_name}-api"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration { scan_on_push = true }
  encryption_configuration { encryption_type = "AES256" }
}

data "aws_iam_policy_document" "lambda_ecr_retrieval" {
  count = var.enable_deployment_resources ? 1 : 0
  statement {
    sid     = "LambdaECRImageRetrievalPolicy"
    actions = ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_ecr_repository_policy" "lambda" {
  count      = var.enable_deployment_resources ? 1 : 0
  repository = aws_ecr_repository.api[0].name
  policy     = data.aws_iam_policy_document.lambda_ecr_retrieval[0].json
}

resource "aws_ecr_lifecycle_policy" "api" {
  count      = var.enable_deployment_resources ? 1 : 0
  repository = aws_ecr_repository.api[0].name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Retain the newest 10 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}
