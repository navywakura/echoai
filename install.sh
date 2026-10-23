#!/usr/bin/env bash
set -euo pipefail
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
py=${ECHO_PYTHON:-python3}
"$py" "$root/tools/source_setup.py" verify --root "$root"
install_root=${ECHO_INSTALL_HOME:-"${XDG_DATA_HOME:-$HOME/.local/share}/echoai/current"}
log_root=${XDG_STATE_HOME:-$HOME/.local/state}/echoai/install
mkdir -p "$log_root"
log="$log_root/$(date -u +%Y%m%dT%H%M%SZ).log"
exec > >(tee "$log") 2>&1
printf '\n  ✦ ECHO-AI 5.8.3\n  Install log: %s\n' "$log"
"$py" -m venv "$install_root/venv"
python_bin="$install_root/venv/bin/python"
"$python_bin" -m pip install "$root[arc]" "$root/harness/echo-nexus"
"$install_root/venv/bin/echoai" verify
bin_dir=${ECHO_BIN_HOME:-$HOME/.local/bin}; mkdir -p "$bin_dir"
for name in echoai echo-dev echo-nexus; do
 target="$bin_dir/$name"
 if [[ -e "$target" && ! -L "$target" ]]; then
  printf 'Existing executable kept: %s. New executable: %s\n' "$target" "$install_root/venv/bin/$name"
 else
  ln -sfn "$install_root/venv/bin/$name" "$target"
 fi
done
printf '\nInstallation verified. Add %s to PATH if needed.\n  echoai setup\n  echoai tui\n' "$bin_dir"
