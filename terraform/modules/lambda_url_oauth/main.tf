# OAuth proxy (KONZEPT section 9): a Lambda Function URL gives the Alexa
# account-linking configuration a stable HTTPS endpoint without an API Gateway.
# The function transparently relays /oauth/* to the home server resolved via
# the S3 beacon. Function URLs use payload format v2.0 — the same event/response
# shape an HTTP API emits — so the handler code is identical either way, and
# they carry no per-request charge (you pay only for the Lambda invocation).

terraform {
  required_version = ">= 1.11"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.7"
    }
  }
}

data "archive_file" "this" {
  type        = "zip"
  source_dir  = var.source_dir
  excludes    = var.source_excludes
  output_path = "${path.module}/build/${var.function_name}.zip"
}

resource "aws_cloudwatch_log_group" "this" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = var.log_retention_days
}

resource "aws_lambda_function" "this" {
  function_name    = var.function_name
  role             = var.role_arn
  runtime          = var.runtime
  handler          = var.handler
  filename         = data.archive_file.this.output_path
  source_code_hash = data.archive_file.this.output_base64sha256
  timeout          = var.timeout_seconds
  memory_size      = var.memory_size_mb

  # Cap the blast radius of a runaway loop: account concurrency is finite and a
  # private OAuth flow is sequential, so a small reservation is plenty.
  reserved_concurrent_executions = var.reserved_concurrency

  # The OAuth proxy never signs requests — it must not receive the shared
  # secret (least privilege, KONZEPT section 9).
  environment {
    variables = {
      TIBERIO_BEACON_BUCKET = var.beacon_bucket_name
      TIBERIO_BEACON_KEY    = var.beacon_object_key
    }
  }

  depends_on = [aws_cloudwatch_log_group.this]
}

# Public HTTPS endpoint for Alexa account linking. AuthType NONE because the
# browser and Alexa reach it unauthenticated; the home server validates the
# OAuth flow itself.
resource "aws_lambda_function_url" "this" {
  function_name      = aws_lambda_function.this.function_name
  authorization_type = "NONE"
}

resource "aws_lambda_permission" "function_url" {
  statement_id           = "AllowPublicFunctionUrl"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.this.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}
