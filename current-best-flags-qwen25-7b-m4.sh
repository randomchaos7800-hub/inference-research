#!/bin/bash
# Qwen2.5-7B-Instruct Q4_K_M — M4 MacBook Air optimal flags
# Autoresearch: 2026-05-22 | llama.cpp 9270
# pp512: ~198 t/s (cold) | tg128: ~21 t/s
# Control: ~/bin/llm {start|stop|status|restart}

llama-server \
  -m ~/models/Qwen2.5-7B-Instruct-Q4_K_M.gguf \
  -ngl 99 \
  -t 1 \
  --flash-attn on \
  -c 8192 \
  --host 127.0.0.1 \
  --port 8080
