#!/usr/bin/env bash
# Compiler control: Vulkan backend built from the SAME tree, SAME commit and
# SAME toolchain as the HIP binary. Removes the GCC-11.4-vs-Clang-22 confound,
# so backend is the only variable between rocm_* and vkclang_* cells.
set -euo pipefail
SRC=$HOME/src/llama.cpp-hip
cd "$SRC"
echo "tree at $(git rev-parse --short HEAD)"
cmake -S . -B build-vk -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_VULKAN=ON \
  -DCMAKE_C_COMPILER=/usr/bin/hipcc \
  -DCMAKE_CXX_COMPILER=/usr/bin/hipcc \
  -DLLAMA_CURL=OFF
cmake --build build-vk --target llama-server -j8
echo "BUILD OK: $SRC/build-vk/bin/llama-server"
"$SRC/build-vk/bin/llama-server" --version 2>&1 | head -3
