#!/usr/bin/env bash
# =============================================================================
# Build the MLOps training source bundle (sourcedir.tar.gz)
# =============================================================================
# SageMaker downloads and extracts `sourcedir.tar.gz` for the training job and
# runs `pip install -r requirements.txt` from inside it before invoking the
# entry-point script. The tarball MUST therefore contain both the training
# script AND requirements.txt, otherwise the sagemaker-mlflow plugin is never
# installed and MLflow rejects the `arn:` tracking URI (KeyError: 'arn').
#
# Re-run this whenever train_xgboost.py or requirements.txt changes so the
# committed tarball does not go stale.
#
# Usage: ./scripts/build-mlops-sourcedir.sh
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$SCRIPT_DIR/../examples/mlops-pipeline/src"

# Files that must be packaged into the training source bundle.
MEMBERS=(train_xgboost.py requirements.txt)

cd "$SRC_DIR"

for f in "${MEMBERS[@]}"; do
  if [ ! -f "$f" ]; then
    echo "ERROR: required file '$f' not found in $SRC_DIR" >&2
    exit 1
  fi
done

tar -czf sourcedir.tar.gz "${MEMBERS[@]}"

echo "Built $(pwd)/sourcedir.tar.gz with: ${MEMBERS[*]}"
tar tzf sourcedir.tar.gz
