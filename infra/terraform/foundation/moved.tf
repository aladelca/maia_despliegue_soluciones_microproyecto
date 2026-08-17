moved {
  from = aws_ecr_repository.api
  to   = aws_ecr_repository.api[0]
}

moved {
  from = aws_ecr_repository_policy.lambda
  to   = aws_ecr_repository_policy.lambda[0]
}

moved {
  from = aws_ecr_lifecycle_policy.api
  to   = aws_ecr_lifecycle_policy.api[0]
}

moved {
  from = aws_iam_openid_connect_provider.github
  to   = aws_iam_openid_connect_provider.github[0]
}

moved {
  from = aws_iam_role.github_actions
  to   = aws_iam_role.github_actions[0]
}

moved {
  from = aws_iam_role_policy.github_actions
  to   = aws_iam_role_policy.github_actions[0]
}
