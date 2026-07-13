#!/usr/bin/env bash
# Installs NEO Piano from GitHub Releases on apt-based NEO One systems.
set -euo pipefail

REPO="lgthevinh/neo-piano"
PKG="neo-piano"
COMMAND="neo-piano"
RAW_INSTALL_URL="https://raw.githubusercontent.com/${REPO}/main/scripts/install_on_neo.sh"

UNINSTALL=false
INSTALL_VERSION=""

for argument in "$@"; do
    case "$argument" in
        --uninstall) UNINSTALL=true ;;
        --version=*)
            INSTALL_VERSION="${argument#*=}"
            INSTALL_VERSION="${INSTALL_VERSION#v}"
            ;;
        *) echo "Unknown option: $argument" >&2; exit 1 ;;
    esac
done

info() { echo -e "\033[1;32m[INFO]\033[0m  $*"; }
error() { echo -e "\033[1;31m[ERROR]\033[0m $*" >&2; }

SUDO="sudo"
if [ "$(id -u)" -eq 0 ]; then
    SUDO=""
fi

cleanup_legacy_install() {
    if command -v python3 >/dev/null 2>&1 \
        && python3 -m pip show "$PKG" >/dev/null 2>&1; then
        local pip_option=""
        if python3 -m pip install --help 2>&1 | grep -q "break-system-packages"; then
            pip_option="--break-system-packages"
        fi
        python3 -m pip uninstall -y $pip_option "$PKG" >/dev/null 2>&1 || true
    fi
    rm -f "$HOME/.local/bin/$COMMAND"
    rm -f "$HOME/.local/share/applications/neo-piano.desktop"
    rm -f "$HOME/.local/share/icons/hicolor/scalable/apps/neo-piano.svg"
}

if [ "$UNINSTALL" = true ]; then
    info "Uninstalling NEO Piano..."
    if command -v apt-get >/dev/null 2>&1 && dpkg -s "$PKG" >/dev/null 2>&1; then
        $SUDO apt-get remove -y "$PKG"
    fi
    cleanup_legacy_install
    info "NEO Piano has been uninstalled."
    exit 0
fi

if ! command -v apt-get >/dev/null 2>&1; then
    error "This installer requires Armbian, Debian, Ubuntu, or another apt-based system."
    exit 1
fi
if ! command -v curl >/dev/null 2>&1; then
    error "curl is required. Install it with: sudo apt-get install curl"
    exit 1
fi

info "Detected architecture: $(dpkg --print-architecture)"

if [ -z "$INSTALL_VERSION" ]; then
    info "Resolving the latest release..."
    INSTALL_VERSION="$(curl -fsSL "https://api.github.com/repos/${REPO}/releases/latest" \
        | sed -nE 's/.*"tag_name": "v?([^"]+)".*/\1/p')"
    if [ -z "$INSTALL_VERSION" ]; then
        error "Could not resolve the latest release."
        error "Pin a version with --version=X.Y.Z."
        exit 1
    fi
fi

DEB_NAME="${PKG}_${INSTALL_VERSION}_all.deb"
DEB_URL="https://github.com/${REPO}/releases/download/v${INSTALL_VERSION}/${DEB_NAME}"
TEMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TEMP_DIR"' EXIT

info "Downloading NEO Piano ${INSTALL_VERSION}..."
curl -fSL --progress-bar -o "$TEMP_DIR/$DEB_NAME" "$DEB_URL"

cleanup_legacy_install

info "Installing NEO Piano and its audio dependencies..."
$SUDO apt-get update -qq || true
$SUDO apt-get install -y "$TEMP_DIR/$DEB_NAME"

if ! command -v "$COMMAND" >/dev/null 2>&1; then
    error "Installation failed: $COMMAND is not available on PATH."
    exit 1
fi

info "Installed NEO Piano ${INSTALL_VERSION}."
echo ""
echo "  Run:       $COMMAND"
echo "  Uninstall: curl -fsSL $RAW_INSTALL_URL | bash -s -- --uninstall"
echo ""
