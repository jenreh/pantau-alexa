variable "name_prefix" {
  description = "Prefix for the IAM role name."
  type        = string
  default     = "tiberio"
}

variable "lambda_function_arns" {
  description = "ARNs of the Lambda functions the deploy role may update."
  type        = list(string)
}

variable "subject_claims" {
  description = <<-EOT
    Allowed GitHub OIDC `sub` claims (StringLike). Defaults scope the role to
    version-tag and main-branch (workflow_dispatch) runs of the repository.
  EOT
  type        = list(string)
}

variable "create_oidc_provider" {
  description = <<-EOT
    Create the GitHub OIDC provider. Set false (and pass
    existing_oidc_provider_arn) if the account already has one — AWS permits
    only a single provider per URL.
  EOT
  type        = bool
  default     = true
}

variable "existing_oidc_provider_arn" {
  description = "ARN of a pre-existing GitHub OIDC provider (when create_oidc_provider = false)."
  type        = string
  default     = null
}
