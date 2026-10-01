#!/usr/bin/env bash
# Build llama.cpp with the HIP/ROCm backend, pinned to the SAME commit as the
# Vulkan binary already on this box (build 11168, 07fc586e3), in a SEPARATE tree.
# ~/opt/llama.cpp and the working Vulkan server are never touched.
set -euo pipefail
TARGET="${1:?usage: build-hip.sh <gfx target>}"
SRC=$HOME/src/llama.cpp-hip
COMMIT=07fc586e3
export PATH=/usr/bin:$PATH
export ROCM_PATH=/usr
export HIP_PATH=/usr

if [ ! -d "$SRC/.git" ]; then
  mkdir -p "$(dirname "$SRC")"
  git clone https://github.com/ggml-org/llama.cpp "$SRC"
fi
cd "$SRC"
git fetch --all --tags 2>/dev/null || true
git checkout -q "$COMMIT" 2>/dev/null || { echo "FATAL: commit $COMMIT not found — backend comparison would be confounded"; exit 1; }
echo "building at $(git rev-parse --short HEAD) for $TARGET"

cmake -S . -B build-hip -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_HIP=ON \
  -DAMDGPU_TARGETS="$TARGET" \
  -DCMAKE_C_COMPILER=/usr/bin/hipcc \
  -DCMAKE_CXX_COMPILER=/usr/bin/hipcc \
  -DLLAMA_CURL=OFF
cmake --build build-hip --target llama-server -j8
echo "BUILD OK: $SRC/build-hip/bin/llama-server"
"$SRC/build-hip/bin/llama-server" --version 2>&1 | head -3
