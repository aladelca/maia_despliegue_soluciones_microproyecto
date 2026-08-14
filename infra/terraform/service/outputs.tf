output "api_base_url" { value = aws_apigatewayv2_api.api.api_endpoint }
output "lambda_function_name" { value = aws_lambda_function.api.function_name }
output "lambda_function_arn" { value = aws_lambda_function.api.arn }
