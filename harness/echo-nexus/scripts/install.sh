#!/usr/bin/env bash
# echo-nexus installer · developer: rxlabs · Copyright (c) 2026 RxLabs · MIT
set -Eeuo pipefail
umask 077

NEXUS_VERSION='1.5.1'
NEXUS_SHA256='8ca50715f812e62c8711e4a1601c30892112c1b1374f0a1c7d4e38aaac0e5df0'
NEXUS_RELEASE="https://www.rxlabs.org/releases/echo-nexus/$NEXUS_VERSION"
NEXUS_WHEEL="echo_nexus-${NEXUS_VERSION}-py3-none-any.whl"
NEXUS_DATA="${ECHO_NEXUS_INSTALL_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/echo-nexus}"
NEXUS_BIN="${ECHO_NEXUS_BIN_DIR:-$HOME/.local/bin}"
NEXUS_STATE="${ECHO_NEXUS_STATE:-${XDG_STATE_HOME:-$HOME/.local/state}/echo-nexus}"
NEXUS_PYTHON="${ECHO_NEXUS_PYTHON:-python3}"
NEXUS_TMP=''
mkdir -p "$NEXUS_STATE/install"
NEXUS_LOG="$NEXUS_STATE/install/$(date -u +%Y%m%dT%H%M%SZ)-$$.log"
exec > >(tee -a "$NEXUS_LOG") 2>&1
trap 'nexus_rc=$?; if [ -n "$NEXUS_TMP" ]; then rm -rf -- "$NEXUS_TMP"; fi; if [ "$nexus_rc" -ne 0 ]; then printf "\nInstallation failed (%s). Log: %s\n" "$nexus_rc" "$NEXUS_LOG"; fi' EXIT

cat <<'BANNER'

     .       *                     .
       E C H O  /  N E X U S    +
     .  observe · connect · verify

     developer: rxlabs
     Copyright (c) 2026 RxLabs · MIT harness

BANNER

case "$(uname -s)" in Linux|Darwin) ;; *) printf 'Use Linux, macOS, or WSL.\n'; exit 1 ;; esac
command -v curl >/dev/null || { printf 'curl is required.\n'; exit 1; }
command -v "$NEXUS_PYTHON" >/dev/null || { printf 'Python 3.10+ is required.\n'; exit 1; }
"$NEXUS_PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' || { printf 'Python 3.10+ is required.\n'; exit 1; }
if [ -e "$NEXUS_BIN/echo-nexus" ] && ! head -n 2 "$NEXUS_BIN/echo-nexus" | grep -q 'echo-nexus-managed'; then
    printf 'A different echo-nexus launcher exists. Choose ECHO_NEXUS_BIN_DIR.\n'
    exit 1
fi
mkdir -p "$NEXUS_DATA" "$NEXUS_BIN"
NEXUS_TMP=$(mktemp -d "${TMPDIR:-/tmp}/echo-nexus-install.XXXXXX")
printf '[1/4] Downloading echo-nexus %s\n' "$NEXUS_VERSION"
curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 --connect-timeout 15 --max-time 120 \
    "$NEXUS_RELEASE/$NEXUS_WHEEL" -o "$NEXUS_TMP/$NEXUS_WHEEL"
"$NEXUS_PYTHON" - "$NEXUS_TMP/$NEXUS_WHEEL" "$NEXUS_SHA256" <<'PY'
import hashlib, pathlib, sys
actual = hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest()
if actual != sys.argv[2]:
    raise SystemExit('Download checksum mismatch. Nothing was installed.')
print('SHA-256 OK:', actual)
PY

printf '[2/4] Creating isolated Python environment (no sudo)\n'
# A unique path leaves a working previous installation untouched if pip fails.
NEXUS_VENV="$NEXUS_DATA/venv-$NEXUS_VERSION-$(date -u +%Y%m%dT%H%M%SZ)-$$"
"$NEXUS_PYTHON" -m venv "$NEXUS_VENV" || { printf 'Install the Python venv package for your OS and retry.\n'; exit 1; }
printf '[3/4] Installing harness and terminal libraries from PyPI\n'
"$NEXUS_VENV/bin/python" -m pip --isolated install --disable-pip-version-check \
    --cache-dir "$NEXUS_DATA/pip-cache" --only-binary=:all: "$NEXUS_TMP/$NEXUS_WHEEL"
"$NEXUS_VENV/bin/python" -m echo_nexus --version
"$NEXUS_PYTHON" - "$NEXUS_VENV" "$NEXUS_BIN" <<'PY'
import os, pathlib, shlex, sys
venv, bindir = map(lambda s: pathlib.Path(s).expanduser().resolve(), sys.argv[1:])
path = bindir / 'echo-nexus'
temp = bindir / ('.echo-nexus-' + str(os.getpid()))
temp.write_text('#!/bin/sh\n# echo-nexus-managed\nexec ' + shlex.quote(str(venv / 'bin/python')) + ' -m echo_nexus "$@"\n')
temp.chmod(0o755)
temp.replace(path)
PY
printf '[4/4] Detecting optional tools (nothing is started)\n'
"$NEXUS_VENV/bin/python" -m echo_nexus --doctor
printf '\nInstalled: %s/echo-nexus\nInstallation log: %s\n' "$NEXUS_BIN" "$NEXUS_LOG"
case ":$PATH:" in *":$NEXUS_BIN:"*) printf 'Start: echo-nexus\n' ;; *) printf 'Add this directory to PATH: %s\nOr start: %s/echo-nexus\n' "$NEXUS_BIN" "$NEXUS_BIN" ;; esac
printf 'Documentation: https://www.rxlabs.org/docs/echoai/echo-nexus\n'
printf 'ECHO core is installed separately. Type /help inside the terminal.\n'
