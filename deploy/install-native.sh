#!/usr/bin/env bash
#
# Install everything this app needs, natively. No Docker.
#
# Safe to re-run: every step checks first and skips what is already present, so
# this doubles as a "is my machine set up correctly?" report.
#
# Works on Fedora/RHEL (dnf) and Debian/Ubuntu (apt). On any other distro it
# tells you what to install by hand rather than guessing.

set -euo pipefail

FABRIC_VERSION="1.4.473"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
PATTERN_DIR="${HOME}/.config/fabric/patterns"

bold() { printf '\n\033[1m%s\033[0m\n' "$1"; }
ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
skip() { printf '  \033[32m✓\033[0m %s (already installed)\n' "$1"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$1"; }
die()  { printf '  \033[31m✗\033[0m %s\n' "$1" >&2; exit 1; }

need_sudo() {
  if [ "$(id -u)" -eq 0 ]; then echo ""; elif command -v sudo >/dev/null; then echo "sudo"; else echo ""; fi
}

pkg_install() {
  # $@ = package names
  local sudo_cmd
  sudo_cmd="$(need_sudo)"
  if command -v dnf >/dev/null; then
    $sudo_cmd dnf install -y "$@"
  elif command -v apt-get >/dev/null; then
    $sudo_cmd apt-get update -qq && $sudo_cmd apt-get install -y "$@"
  else
    die "No dnf or apt-get found. Install these by hand, then re-run: $*"
  fi
}

bold "1. Audio tooling (ffmpeg + ffprobe)"
if command -v ffmpeg >/dev/null && command -v ffprobe >/dev/null; then
  skip "ffmpeg $(ffmpeg -version 2>/dev/null | head -1 | awk '{print $3}') and ffprobe"
else
  # ffprobe is NOT optional: the transcriber uses it to work out chunk
  # boundaries, and transcription fails outright without it. On most distros it
  # arrives with ffmpeg, which is why only ffmpeg is named here.
  warn "installing ffmpeg"
  pkg_install ffmpeg
  command -v ffprobe >/dev/null || die "ffmpeg installed but ffprobe is still missing. Install it separately."
  ok "ffmpeg and ffprobe installed"
fi

bold "2. Python environment"
cd "$PROJECT_DIR"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  ok "created .venv"
else
  skip ".venv"
fi
# Invoke pip as a module: the console script in .venv/bin hard-codes an absolute
# interpreter path at install time and breaks silently if the venv is ever moved.
.venv/bin/python3 -m pip install --quiet --upgrade pip
.venv/bin/python3 -m pip install --quiet -r backend/requirements.txt yt-dlp
ok "Python dependencies and yt-dlp installed"

bold "3. fabric CLI"
if command -v fabric >/dev/null; then
  skip "fabric $(fabric --version 2>/dev/null | head -1)"
else
  case "$(uname -m)" in
    x86_64)         asset="fabric_Linux_x86_64.tar.gz" ;;
    aarch64|arm64)  asset="fabric_Linux_arm64.tar.gz" ;;
    *) die "Unsupported architecture $(uname -m). Download fabric manually." ;;
  esac
  base="https://github.com/danielmiessler/fabric/releases/download/v${FABRIC_VERSION}"
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT

  warn "downloading fabric v${FABRIC_VERSION} (${asset})"
  curl -fsSL -o "$tmp/$asset" "$base/$asset"
  # Verified against the checksums published with the same release, so the
  # version pin actually means something.
  curl -fsSL -o "$tmp/checksums.txt" "$base/fabric_${FABRIC_VERSION}_checksums.txt"
  ( cd "$tmp" && grep " ${asset}\$" checksums.txt | sha256sum -c - >/dev/null ) \
    || die "fabric checksum verification FAILED — refusing to install it"

  tar -xzf "$tmp/$asset" -C "$tmp" fabric
  mkdir -p "$BIN_DIR"
  install -m 0755 "$tmp/fabric" "$BIN_DIR/fabric"
  rm -rf "$tmp"; trap - EXIT
  ok "fabric installed to $BIN_DIR/fabric (checksum verified)"
  case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) warn "$BIN_DIR is not on your PATH — add it, or run fabric as $BIN_DIR/fabric" ;;
  esac
fi

bold "4. fabric patterns"
if [ ! -d "$PROJECT_DIR/fabric-patterns" ]; then
  warn "fabric-patterns/ is missing from the repo — patterns cannot be installed"
else
  mkdir -p "$PATTERN_DIR"
  # The patterns are vendored in the repo so the install never depends on GitHub
  # being reachable at the moment you happen to deploy.
  #
  # -n (no-clobber) so this only fills in what is missing. Overwriting would
  # silently revert any pattern you had edited, and would undo a later
  # `fabric -U` every time this script was re-run.
  cp -rn "$PROJECT_DIR/fabric-patterns/." "$PATTERN_DIR/"
  rm -f "$PATTERN_DIR/loaded"   # fabric's own state marker, not content
  ok "$(find "$PATTERN_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l) patterns available in $PATTERN_DIR"
fi

bold "5. Frontend"
if [ ! -d frontend/node_modules ]; then
  warn "installing npm packages"
  ( cd frontend && npm install --silent )
  ok "npm packages installed"
else
  skip "node_modules"
fi
( cd frontend && npm run build >/dev/null 2>&1 ) || die "frontend build failed — run 'cd frontend && npm run build' to see why"
ok "frontend built"

bold "6. OpenRouter API key"
if [ -n "${OPENROUTER_API_KEY:-}" ]; then
  ok "OPENROUTER_API_KEY is set in the environment"
elif [ -f "$HOME/.config/fabric/.env" ] && grep -q '^OPENROUTER_API_KEY=' "$HOME/.config/fabric/.env"; then
  ok "OPENROUTER_API_KEY found in ~/.config/fabric/.env"
else
  warn "No OpenRouter API key found. Transcriptions will fail."
  warn "Put OPENROUTER_API_KEY=sk-or-... in ~/.config/fabric/.env, or export it."
fi

bold "Done"
cat <<EOF
  Start the app:      ./backend/run.sh
  Then open:          http://localhost:5173

  To deploy for testers, see "Deploying (Netlify + Render)" in README.md.
EOF
