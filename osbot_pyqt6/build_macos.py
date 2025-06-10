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
SCRIPT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
if SCRIPT_DIR.name == "osbot_pyqt6":
    # Script is being run from within osbot_pyqt6 directory
    PROJECT_ROOT = SCRIPT_DIR.parent
    OSBOT_DIR = SCRIPT_DIR
else:
    # Script is being run from project root
    PROJECT_ROOT = SCRIPT_DIR
    OSBOT_DIR = PROJECT_ROOT / "osbot_pyqt6"

DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
ASSETS_DIR = PROJECT_ROOT / "assets"

# Create necessary directories
os.makedirs(DIST_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

# Application metadata
APP_NAME = "Web Content Capture"
APP_IDENTIFIER = "com.osbot.webcapture"
APP_VERSION = "1.0.0"


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
        "pydantic",
        "mitmproxy",
        "requests",
        "osbot-utils"
    ]

    print("Installing dependencies...")
    cmd = ["pip", "install"] + dependencies
    return run_command(cmd, "Failed to install dependencies")


def create_icon():
    """Create a placeholder icon if it doesn't exist"""
    icon_path = ASSETS_DIR / "app_icon.icns"
    if not icon_path.exists():
        print("Creating placeholder icon...")
        # Create a simple icon using iconutil (macOS built-in)
        iconset_path = ASSETS_DIR / "app_icon.iconset"
        os.makedirs(iconset_path, exist_ok=True)

        # Create placeholder PNG files for different sizes
        sizes = [16, 32, 64, 128, 256, 512]
        for size in sizes:
            # You can replace this with actual icon generation
            print(f"  - Would create {size}x{size} icon")

        print("WARNING: No app icon found. A default icon will be used.")

    return icon_path


def build_app_with_pyinstaller():
    """Build the application using PyInstaller"""
    print(f"Building {APP_NAME} with PyInstaller...")

    # Clean previous builds
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)

    # Icon path
    icon_path = create_icon()

    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--name", APP_NAME,  # Keep spaces in name for proper .app bundle
        "--windowed",
        "--onedir",  # Use onedir for .app bundle
        "--clean",
        "--noconfirm",
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR),
        "--specpath", str(PROJECT_ROOT),
        "--osx-bundle-identifier", APP_IDENTIFIER,
    ]

    # Add paths for imports
    cmd.extend(["--paths", str(OSBOT_DIR)])
    cmd.extend(["--paths", str(PROJECT_ROOT)])

    # Add data files
    data_files = [
        # Main application files
        (str(OSBOT_DIR / "server.py"), "osbot_pyqt6"),
        (str(OSBOT_DIR / "start_mitmproxy.py"), "osbot_pyqt6"),
        (str(OSBOT_DIR / "content_replacer.py"), "osbot_pyqt6"),
        (str(OSBOT_DIR / "aggressive_ssl_bypass.py"), "osbot_pyqt6"),
        (str(OSBOT_DIR / "main_app.py"), "osbot_pyqt6"),
        (str(OSBOT_DIR / "__init__.py"), "osbot_pyqt6"),

        # Utils folder
        (str(OSBOT_DIR / "utils" / "__init__.py"), "osbot_pyqt6/utils"),
        (str(OSBOT_DIR / "utils" / "Version.py"), "osbot_pyqt6/utils"),
    ]

    # Add version file if it exists
    version_file = OSBOT_DIR / "version"
    if version_file.exists():
        data_files.append((str(version_file), "osbot_pyqt6"))

    # Check all files exist before adding
    for src, dst in data_files:
        if not Path(src).exists():
            print(f"WARNING: File not found: {src}")
        else:
            cmd.extend(["--add-data", f"{src}:{dst}"])

    # Collect all imports from the project
    cmd.extend(["--collect-all", "osbot_pyqt6"])

    # Add hidden imports
    hidden_imports = [
        # Standard imports
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "fastapi",
        "starlette",
        "mitmproxy",
        "mitmproxy.tools",
        "mitmproxy.tools.dump",
        "mitmproxy.http",
        "mitmproxy.options",
        "mitmproxy.master",
        "mitmproxy.ctx",
        "osbot_utils",
        "osbot_utils.type_safe",
        "osbot_utils.type_safe.Type_Safe",
        "osbot_utils.utils",
        "osbot_utils.utils.Files",
        "osbot_utils.helpers",
        "osbot_utils.helpers.duration",
        "osbot_utils.helpers.duration.decorators",
        "osbot_utils.helpers.duration.decorators.capture_duration",
        # PyQt6 specific
        "PyQt6.QtWidgets",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWebEngineWidgets",
        "PyQt6.QtWebEngineCore",
        "PyQt6.QtNetwork",
        # Python standard library that might be needed
        "asyncio",
        "threading",
        "json",
        "pathlib",
        "tempfile",
        "signal",
        "atexit",
    ]

    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    # Add icon if available
    if icon_path.exists():
        cmd.extend(["--icon", str(icon_path)])

    # Add the main script
    cmd.append(str(OSBOT_DIR / "main_app.py"))

    # Run PyInstaller
    print("Running PyInstaller with command:")
    print(" ".join(cmd))

    success = run_command(cmd, "PyInstaller build failed")

    if success:
        print("Build completed, checking output...")

        # List what was actually built
        if DIST_DIR.exists():
            print(f"Contents of {DIST_DIR}:")
            for item in DIST_DIR.iterdir():
                print(f"  - {item}")
                if item.is_dir() and item.name.endswith(".app"):
                    # Check app bundle structure
                    contents_dir = item / "Contents"
                    macos_dir = contents_dir / "MacOS"
                    if macos_dir.exists():
                        print(f"    Executables in MacOS folder:")
                        for exe in macos_dir.iterdir():
                            print(f"      - {exe.name}")

    # Clean up spec file if it exists
    spec_file = PROJECT_ROOT / f"{APP_NAME}.spec"
    if spec_file.exists():
        os.remove(spec_file)

    return success


def sign_application(cert_name):
    """Sign the application with an Apple Developer certificate"""
    print(f"Signing application with certificate: {cert_name}")

    app_path = DIST_DIR / f"{APP_NAME}.app"

    if not app_path.exists():
        print(f"ERROR: Application not found at {app_path}")
        return False

    # Sign all frameworks and dylibs first
    frameworks_path = app_path / "Contents" / "Frameworks"
    if frameworks_path.exists():
        print("Signing frameworks...")
        for framework in frameworks_path.rglob("*.framework"):
            cmd = [
                "codesign",
                "--force",
                "--deep",
                "--sign", cert_name,
                str(framework)
            ]
            run_command(cmd, f"Failed to sign {framework.name}")

        for dylib in frameworks_path.rglob("*.dylib"):
            cmd = [
                "codesign",
                "--force",
                "--sign", cert_name,
                str(dylib)
            ]
            run_command(cmd, f"Failed to sign {dylib.name}")

    # Sign the main app bundle
    cmd = [
        "codesign",
        "--force",
        "--deep",
        "--verbose",
        "--sign", cert_name,
        "--options", "runtime",
        "--entitlements", "-",  # Use default entitlements
        str(app_path)
    ]

    return run_command(cmd, "Failed to sign application")


def create_dmg():
    """Create a DMG file for distribution"""
    print("Creating DMG file...")

    # Find the app first
    possible_app_locations = [
        DIST_DIR / f"{APP_NAME}.app",
        DIST_DIR / f"{APP_NAME.replace(' ', '')}.app",
        DIST_DIR / APP_NAME.replace(" ", "") / f"{APP_NAME}.app",
        DIST_DIR / APP_NAME.replace(" ", "") / f"{APP_NAME.replace(' ', '')}.app",
    ]

    app_path = None
    for location in possible_app_locations:
        if location.exists():
            app_path = location
            break

    if not app_path:
        print(f"ERROR: Application not found in any expected location")
        return False

    dmg_path = DIST_DIR / f"{APP_NAME.replace(' ', '-')}-{APP_VERSION}.dmg"

    # Remove old DMG if it exists
    if dmg_path.exists():
        os.remove(dmg_path)

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
        print(f"✅ DMG created at: {dmg_path}")

        # Sign the DMG if we're signing
        if args.sign and args.cert_name:
            print("Signing DMG...")
            sign_cmd = [
                "codesign",
                "--force",
                "--sign", args.cert_name,
                str(dmg_path)
            ]
            run_command(sign_cmd, "Failed to sign DMG")

    return success


def create_entitlements():
    """Create entitlements file for the app"""
    entitlements = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
    <key>com.apple.security.network.client</key>
    <true/>
    <key>com.apple.security.network.server</key>
    <true/>
</dict>
</plist>"""

    entitlements_path = PROJECT_ROOT / "entitlements.plist"
    with open(entitlements_path, 'w') as f:
        f.write(entitlements)

    return entitlements_path


def main():
    """Main build process"""
    print(f"Building {APP_NAME} v{APP_VERSION} for macOS")
    print("=" * 60)

    # Check if we're in the right directory
    if not OSBOT_DIR.exists():
        print(f"ERROR: osbot_pyqt6 directory not found at {OSBOT_DIR}")
        print("Please run this script from the project root directory or from within osbot_pyqt6")
        return

    print(f"Project root: {PROJECT_ROOT}")
    print(f"OWASP directory: {OSBOT_DIR}")
    print(f"Build output: {DIST_DIR}")

    # Prepare build environment
    if not install_dependencies():
        return

    # Create entitlements
    entitlements_path = create_entitlements()

    # Build the app
    if not build_app_with_pyinstaller():
        return

    # Check where the app was actually built
    possible_app_locations = [
        DIST_DIR / f"{APP_NAME}.app",
        DIST_DIR / f"{APP_NAME.replace(' ', '')}.app",
        DIST_DIR / APP_NAME.replace(" ", "") / f"{APP_NAME}.app",
        DIST_DIR / APP_NAME.replace(" ", "") / f"{APP_NAME.replace(' ', '')}.app",
    ]

    app_path = None
    for location in possible_app_locations:
        if location.exists():
            app_path = location
            print(f"Found app at: {app_path}")
            break

    if not app_path:
        print("ERROR: Could not find built application.")
        print("Searched in:")
        for loc in possible_app_locations:
            print(f"  - {loc}")
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

    # Clean up
    if entitlements_path.exists():
        os.remove(entitlements_path)

    print(f"\n✅ Build completed successfully!")
    print(f"Application bundle: {app_path}")
    dmg_name = f"{APP_NAME.replace(' ', '-')}-{APP_VERSION}.dmg"
    print(f"DMG installer: {DIST_DIR / dmg_name}")
    print("\nTo run the app directly:")
    print(f"  open '{app_path}'")


if __name__ == "__main__":
    main()