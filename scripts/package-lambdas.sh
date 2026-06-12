#!/usr/bin/env bash
set -euo pipefail

# ════════════════════════════════════════════════════════════════════════════════
# Package the edge Lambda functions into deployable zips.
#
# Mirrors the layout produced by Terraform's archive_file (terraform/modules/
# lambda_*): each zip is rooted at the lambda/ directory so the handler module
# (e.g. directive_proxy.handler.handler) can import the sibling shared/ package.
#
#   tiberio-directive-proxy.zip  ->  directive_proxy/ + shared/
#   tiberio-oauth-proxy.zip      ->  oauth_proxy/     + shared/
#
# Output: dist/lambda/<function>.zip
# Used by both CI (.github/workflows/deploy-lambda.yml) and `task deploy:push`.
# ════════════════════════════════════════════════════════════════════════════════

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LAMBDA_DIR="$ROOT_DIR/lambda"
DIST_DIR="$ROOT_DIR/dist/lambda"

rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"

# package <function-name> <dir>...
# Zips the given directories (rooted at lambda/) excluding compiled artifacts,
# matching the source_excludes in the Terraform modules.
package() {
  local name="$1"
  shift
  local zip="$DIST_DIR/$name.zip"
  (cd "$LAMBDA_DIR" && zip -qr -X "$zip" "$@" -x '*__pycache__*' '*.pyc')
  echo "Built $zip ($(du -h "$zip" | cut -f1))"
}

package "tiberio-directive-proxy" directive_proxy shared
package "tiberio-oauth-proxy" oauth_proxy shared
