output "deploy_role_arn" {
  description = "ARN of the GitHub Actions deploy role (set as the AWS_DEPLOY_ROLE_ARN repo variable)."
  value       = aws_iam_role.deploy.arn
}

output "oidc_provider_arn" {
  description = "ARN of the GitHub OIDC provider used by the deploy role."
  value       = local.provider_arn
}
