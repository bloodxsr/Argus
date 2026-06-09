#!/usr/bin/env bash
set -euo pipefail
# Wrapper to run the fine-tune script under `accelerate launch` using the example config.
ROOT_DIR="$(cd "$(dirname "$0")" && pwd -P)/.."
SCRIPT="$ROOT_DIR/train/fine_tune_lora.py"
CONFIG="$ROOT_DIR/train/accelerate_config.yaml"

if ! command -v accelerate >/dev/null 2>&1; then
  echo "Please install 'accelerate' and configure your environment first."
  exit 2
fi

accelerate launch --config_file "$CONFIG" "$SCRIPT" "$@"
