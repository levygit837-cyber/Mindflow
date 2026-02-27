#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python -m grpc_tools.protoc \
  -I ./omnimind_backend/grpc/proto \
  --python_out=./omnimind_backend/grpc/generated \
  --grpc_python_out=./omnimind_backend/grpc/generated \
  ./omnimind_backend/grpc/proto/omnimind_backend.proto
