# GitHub Actions OIDC deploy role: lets the deploy-lambda workflow assume a
# least-privilege role via short-lived OIDC tokens (no static access keys).
# The role may only update the code of the two edge Lambda functions.

terraform {
  required_version = ">= 1.11"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

locals {
  oidc_url     = "https://token.actions.githubusercontent.com"
  provider_arn = var.create_oidc_provider ? aws_iam_openid_connect_provider.github[0].arn : var.existing_oidc_provider_arn
}

# An AWS account can hold only one OIDC provider per URL. Set
# create_oidc_provider = false and pass existing_oidc_provider_arn if the
# GitHub provider already exists in the account.
resource "aws_iam_openid_connect_provider" "github" {
  count = var.create_oidc_provider ? 1 : 0

  url            = local.oidc_url
  client_id_list = ["sts.amazonaws.com"]
  # AWS validates GitHub's OIDC tokens against its trusted CA library; the
  # thumbprint is no longer used for verification but the argument is required.
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [local.provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    # Restrict to the configured repo refs (tags + branches) so only this
    # repository's workflows can assume the role.
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = var.subject_claims
    }
  }
}

resource "aws_iam_role" "deploy" {
  name               = "${var.name_prefix}-github-deploy"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

# Least privilege: update/publish code and read config for the two functions only.
data "aws_iam_policy_document" "deploy" {
  statement {
    sid = "DeployLambdaCode"
    actions = [
      "lambda:UpdateFunctionCode",
      "lambda:PublishVersion",
      "lambda:GetFunction",
    ]
    resources = var.lambda_function_arns
  }
}

resource "aws_iam_role_policy" "deploy" {
  name   = "${var.name_prefix}-github-deploy-access"
  role   = aws_iam_role.deploy.id
  policy = data.aws_iam_policy_document.deploy.json
}
