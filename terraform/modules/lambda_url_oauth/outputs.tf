locals {
  # aws_lambda_function_url.function_url carries a trailing slash; drop it so
  # the path joins cleanly.
  base_url = trimsuffix(aws_lambda_function_url.this.function_url, "/")
}

output "api_endpoint" {
  description = "Base endpoint of the OAuth Lambda Function URL."
  value       = local.base_url
}

output "authorize_url" {
  description = "Authorization URI for the Alexa account-linking configuration."
  value       = "${local.base_url}/oauth/authorize"
}

output "token_url" {
  description = "Access token URI for the Alexa account-linking configuration."
  value       = "${local.base_url}/oauth/token"
}

output "function_arn" {
  description = "ARN of the OAuth proxy Lambda function."
  value       = aws_lambda_function.this.arn
}
