#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python -m grpc_tools.protoc \
  -I ./mindflow_backend/grpc/proto \
  --python_out=./mindflow_backend/grpc/generated \
  --grpc_python_out=./mindflow_backend/grpc/generated \
  ./mindflow_backend/grpc/proto/mindflow_backend.proto
