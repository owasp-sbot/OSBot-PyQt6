#!/usr/bin/env python3
"""
Build script for creating a macOS application bundle for Web Content Capture.
This script uses PyInstaller to create a single, self-contained .app file.

Requirements:
- PyInstaller: pip install pyinstaller
- All dependencies for the application
- Certificate for code signing (optional)

Usage:
python build_macos.py [--sign]

Options:
--sign: Sign the application with your Apple Developer certificate
"""

import os
import subprocess
import argparse
import shutil
import platform
from pathlib import Path

# Ensure we're on macOS
if platform.system() != "Darwin":
    print("This script is for macOS only!")
    exit(1)

# Parse arguments
parser = argparse.ArgumentParser(description="Build macOS application for Web Content Capture")
parser.add_argument("--sign", action="store_true", help="Sign the application with an Apple Developer certificate")
parser.add_argument("--cert-name", type=str, default=None, help="Certificate name to use for signing")
args = parser.parse_args()

# Project directories
PROJECT_ROOT = Path(os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
ASSETS_DIR = PROJECT_ROOT / "assets"

# Create necessary directories
os.makedirs(DIST_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

# Application metadata
APP_NAME = "Web Content Capture"
APP_IDENTIFIER = "com.example.WebContentCapture"
APP_VERSION = "0.1.0"


def run_command(command, error_msg=None):
    """Run a shell command and handle errors"""
    try:
        print(f"Running: {' '.join(command)}")
        subprocess.run(command, check=True)
        return True
    except subprocess.CalledProcessError as e:
        if error_msg:
            print(f"ERROR: {error_msg}")
        print(f"Command failed with exit code {e.returncode}: {e}")
        return False

def install_dependencies():
    """Install required dependencies"""
    dependencies = [
        "PyQt6",
        "PyQt6-WebEngine",
        "fastapi",
        "uvicorn[standard]",
        "pyinstaller",
        "python-multipart",
        "starlette",
        "pydantic"
    ]

    print("Installing dependencies...")
    cmd = ["pip", "install"] + dependencies
    return run_command(cmd, "Failed to install dependencies")


def build_app_with_pyinstaller():
    """Build the application using PyInstaller"""
    print(f"Building {APP_NAME} with PyInstaller...")

    # Clean previous builds
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)

    # Icon path (create a placeholder if it doesn't exist)
    icon_path = ASSETS_DIR / "app_icon.icns"
    if not icon_path.exists():
        print("WARNING: No app icon found. A default icon will be used.")
        # In a real scenario, you would create or copy an icon file here

    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--name", APP_NAME.replace(" ", ""),
        "--windowed",
        "--onefile",
        "--clean",
        "--noconfirm",
        "--add-data", f"{PROJECT_ROOT / 'server.py'}:.",
        "--add-data", f"{PROJECT_ROOT / 'client.py'}:.",
        "--collect-all", "uvicorn",
        "--collect-all", "fastapi",
        f"{PROJECT_ROOT / 'main_app.py'}"
    ]

    # Add icon if available
    if icon_path.exists():
        cmd.extend(["--icon", str(icon_path)])

    return run_command(cmd, "PyInstaller build failed")


def sign_application(cert_name):
    """Sign the application with an Apple Developer certificate"""
    print(f"Signing application with certificate: {cert_name}")

    app_path = DIST_DIR / f"{APP_NAME.replace(' ', '')}.app"

    if not app_path.exists():
        print(f"ERROR: Application not found at {app_path}")
        return False

    # Sign the app
    cmd = [
        "codesign",
        "--force",
        "--verbose",
        "--sign", cert_name,
        "--options", "runtime",
        str(app_path)
    ]

    return run_command(cmd, "Failed to sign application")


def create_dmg():
    """Create a DMG file for distribution"""
    print("Creating DMG file...")

    app_name_no_spaces = APP_NAME.replace(" ", "")
    app_path = DIST_DIR / f"{app_name_no_spaces}.app"
    dmg_path = DIST_DIR / f"{app_name_no_spaces}-{APP_VERSION}.dmg"

    if not app_path.exists():
        print(f"ERROR: Application not found at {app_path}")
        return False

    # Create a DMG
    cmd = [
        "hdiutil", "create",
        "-volname", APP_NAME,
        "-srcfolder", str(app_path),
        "-ov", "-format", "UDZO",
        str(dmg_path)
    ]

    success = run_command(cmd, "Failed to create DMG")

    if success:
        print(f"DMG created at: {dmg_path}")

    return success


def main():
    """Main build process"""
    print(f"Building {APP_NAME} v{APP_VERSION} for macOS")

    # Prepare build environment
    if not install_dependencies():
        return

    # Build the app
    if not build_app_with_pyinstaller():
        return

    # Sign the app if requested
    if args.sign:
        cert_name = args.cert_name
        if not cert_name:
            print("ERROR: Certificate name must be provided with --cert-name when using --sign")
            return

        if not sign_application(cert_name):
            return

    # Create DMG for distribution
    if not create_dmg():
        return

    print(f"\n✅ Build completed successfully!")
    print(f"Application bundle: {DIST_DIR / f'{APP_NAME.replace(" ", "")}.app'}")
    print(f"DMG installer: {DIST_DIR / f'{APP_NAME.replace(" ", "")}-{APP_VERSION}.dmg'}")


if __name__ == "__main__":
    main()