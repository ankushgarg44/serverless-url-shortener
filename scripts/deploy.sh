#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAMBDA_DIR="${SCRIPT_DIR}/../lambda"

cd "${LAMBDA_DIR}"
zip -j -X -q -FS shorten_url.zip shorten_url.py
zip -j -X -q -FS redirect_url.zip redirect_url.py
zip -j -X -q -FS frontend.zip frontend.py index.html

echo "Packaged all Lambda functions."
