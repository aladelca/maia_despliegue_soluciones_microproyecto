moved {
  from = aws_iam_role.lambda
  to   = aws_iam_role.lambda[0]
}

moved {
  from = aws_iam_role_policy_attachment.lambda_logs
  to   = aws_iam_role_policy_attachment.lambda_logs[0]
}
