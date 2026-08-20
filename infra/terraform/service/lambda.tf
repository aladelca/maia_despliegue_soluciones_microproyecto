resource "aws_lambda_function" "api" {
  function_name = "${var.project_name}-${var.environment}-api"
  role = (
    var.lambda_execution_role_arn != null
    ? var.lambda_execution_role_arn
    : aws_iam_role.lambda[0].arn
  )
  package_type  = "Image"
  image_uri     = var.image_uri
  architectures = ["x86_64"]
  memory_size   = var.lambda_memory_mb
  timeout       = var.lambda_timeout_seconds

  environment {
    variables = { ALLOWED_ORIGIN = var.allowed_origin }
  }
}
