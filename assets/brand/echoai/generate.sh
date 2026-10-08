#!/usr/bin/env bash
# Mechanical resizing only. Never redraw, crop or overwrite the original.
set -euo pipefail
brand_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
brand_source="$brand_dir/../../../echo-ai-agent-logo.png"
command -v magick >/dev/null
for brand_size in 16 32 48 64 128 180 192 256 512 1024; do
  magick "$brand_source" -filter Lanczos -resize "${brand_size}x${brand_size}" \
    -strip -define png:exclude-chunks=date,time "$brand_dir/echoai-${brand_size}.png"
done
magick "$brand_source" -strip -define icon:auto-resize=48,32,16 "$brand_dir/favicon.ico"
magick identify "$brand_dir/echoai-16.png" "$brand_dir/echoai-1024.png" "$brand_dir/favicon.ico"
