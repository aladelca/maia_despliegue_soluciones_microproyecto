data "tls_certificate" "github" {
  count = var.enable_deployment_resources ? 1 : 0
  url   = "https://token.actions.githubusercontent.com"
}

data "aws_caller_identity" "current" {
  count = var.enable_deployment_resources ? 1 : 0
}

data "aws_partition" "current" {
  count = var.enable_deployment_resources ? 1 : 0
}

resource "aws_iam_openid_connect_provider" "github" {
  count           = var.enable_deployment_resources ? 1 : 0
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.github[0].certificates[0].sha1_fingerprint]
}

data "aws_iam_policy_document" "github_assume_role" {
  count = var.enable_deployment_resources ? 1 : 0
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github[0].arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values = [
        "repo:${var.github_owner}/${var.github_repository}:ref:refs/heads/main",
        "repo:${var.github_owner}/${var.github_repository}:environment:${var.environment}",
      ]
    }
  }
}

resource "aws_iam_role" "github_actions" {
  count              = var.enable_deployment_resources ? 1 : 0
  name               = "${var.project_name}-github-actions"
  assume_role_policy = data.aws_iam_policy_document.github_assume_role[0].json
}

data "aws_iam_policy_document" "github_permissions" {
  count = var.enable_deployment_resources ? 1 : 0
  statement {
    actions = [
      "ecr:GetAuthorizationToken",
    ]
    resources = ["*"]
  }
  statement {
    actions = [
      "ecr:BatchGetImage",
      "ecr:BatchCheckLayerAvailability",
      "ecr:CompleteLayerUpload",
      "ecr:DescribeImages",
      "ecr:GetRepositoryPolicy",
      "ecr:GetDownloadUrlForLayer",
      "ecr:InitiateLayerUpload",
      "ecr:PutImage",
      "ecr:SetRepositoryPolicy",
      "ecr:UploadLayerPart",
    ]
    resources = [aws_ecr_repository.api[0].arn]
  }
  statement {
    actions   = ["s3:GetObject", "s3:ListBucket"]
    resources = [aws_s3_bucket.dvc.arn, "${aws_s3_bucket.dvc.arn}/*"]
  }
  statement {
    actions = [
      "s3:DeleteObject",
      "s3:GetObject",
      "s3:PutObject",
    ]
    resources = [
      "arn:${data.aws_partition.current[0].partition}:s3:::${var.terraform_state_bucket_name}/online-shoppers/dev/service.tfstate",
      "arn:${data.aws_partition.current[0].partition}:s3:::${var.terraform_state_bucket_name}/online-shoppers/dev/service.tfstate.tflock",
    ]
  }
  statement {
    actions = [
      "s3:GetBucketLocation",
      "s3:ListBucket",
    ]
    resources = ["arn:${data.aws_partition.current[0].partition}:s3:::${var.terraform_state_bucket_name}"]
  }
  statement {
    actions = [
      "lambda:AddPermission",
      "lambda:CreateFunction",
      "lambda:DeleteFunction",
      "lambda:GetFunction",
      "lambda:GetFunctionCodeSigningConfig",
      "lambda:GetPolicy",
      "lambda:ListTags",
      "lambda:RemovePermission",
      "lambda:TagResource",
      "lambda:UntagResource",
      "lambda:UpdateFunctionCode",
      "lambda:UpdateFunctionConfiguration",
    ]
    resources = [
      "arn:${data.aws_partition.current[0].partition}:lambda:${var.aws_region}:${data.aws_caller_identity.current[0].account_id}:function:${var.project_name}-${var.environment}-api",
    ]
  }
  statement {
    actions = [
      "iam:AttachRolePolicy",
      "iam:CreateRole",
      "iam:DeleteRole",
      "iam:DetachRolePolicy",
      "iam:GetRole",
      "iam:ListAttachedRolePolicies",
      "iam:ListRolePolicies",
      "iam:PassRole",
      "iam:TagRole",
      "iam:UntagRole",
      "iam:UpdateAssumeRolePolicy",
    ]
    resources = [
      "arn:${data.aws_partition.current[0].partition}:iam::${data.aws_caller_identity.current[0].account_id}:role/${var.project_name}-${var.environment}-lambda",
    ]
  }
  statement {
    actions = [
      "apigateway:DELETE",
      "apigateway:GET",
      "apigateway:PATCH",
      "apigateway:POST",
      "apigateway:PUT",
    ]
    resources = [
      "arn:${data.aws_partition.current[0].partition}:apigateway:${var.aws_region}::/apis*",
      "arn:${data.aws_partition.current[0].partition}:apigateway:${var.aws_region}::/tags/*",
    ]
  }
  statement {
    actions = [
      "logs:CreateLogGroup",
      "logs:DeleteLogGroup",
      "logs:ListTagsForResource",
      "logs:PutRetentionPolicy",
      "logs:TagResource",
      "logs:UntagResource",
    ]
    resources = [
      "arn:${data.aws_partition.current[0].partition}:logs:${var.aws_region}:${data.aws_caller_identity.current[0].account_id}:log-group:/aws/lambda/${var.project_name}-${var.environment}-api*",
      "arn:${data.aws_partition.current[0].partition}:logs:${var.aws_region}:${data.aws_caller_identity.current[0].account_id}:log-group:/aws/api-gateway/${var.project_name}-${var.environment}*",
    ]
  }
  statement {
    actions = [
      "cloudwatch:DeleteAlarms",
      "cloudwatch:PutMetricAlarm",
      "cloudwatch:TagResource",
      "cloudwatch:UntagResource",
    ]
    resources = [
      "arn:${data.aws_partition.current[0].partition}:cloudwatch:${var.aws_region}:${data.aws_caller_identity.current[0].account_id}:alarm:${var.project_name}-${var.environment}-*",
    ]
  }
  statement {
    actions = [
      "cloudwatch:DescribeAlarms",
      "logs:DescribeLogGroups",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "github_actions" {
  count  = var.enable_deployment_resources ? 1 : 0
  name   = "${var.project_name}-github-actions"
  role   = aws_iam_role.github_actions[0].id
  policy = data.aws_iam_policy_document.github_permissions[0].json
}
