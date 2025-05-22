#!/usr/bin/env python3
"""
More aggressive SSL bypass approach for QtWebEngine
This sets environment variables and uses multiple methods to ensure SSL bypass works
"""

import os
import sys


# Set environment variables BEFORE any Qt imports
# These affect Chromium's behavior at the lowest level
def setup_chromium_environment():
    """Set environment variables that affect Chromium/QtWebEngine SSL behavior"""

    # Disable SSL verification at the Chromium level
    chromium_env_vars = {
        'QTWEBENGINE_CHROMIUM_FLAGS': (
            '--ignore-certificate-errors '
            '--ignore-ssl-errors '
            '--ignore-certificate-errors-spki-list '
            '--ignore-urlfetcher-cert-requests '
            '--disable-web-security '
            '--allow-running-insecure-content '
            '--disable-features=VizDisplayCompositor '
            '--disable-extensions '
            '--no-sandbox '
            '--disable-dev-shm-usage '
            '--disable-gpu-sandbox '
            '--ignore-certificate-errors-policy '
            '--allow-running-insecure-content '
            '--disable-background-timer-throttling '
            '--disable-backgrounding-occluded-windows '
            '--disable-renderer-backgrounding '
            '--disable-field-trial-config '
            '--disable-ipc-flooding-protection'
        ),
        'QTWEBENGINE_DISABLE_SANDBOX': '1',
        'QTWEBENGINE_REMOTE_DEBUGGING': '9222'
    }

    print("🔧 Setting Chromium environment variables...")
    for key, value in chromium_env_vars.items():
        os.environ[key] = value
        print(f"   {key}={value}")

    return chromium_env_vars


# Apply environment setup IMMEDIATELY
setup_chromium_environment()

import signal
import subprocess
import time
import threading
import argparse
import atexit
import requests
import tempfile
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QToolBar, QLineEdit, QPushButton, \
    QStatusBar, QMessageBox
from PyQt6.QtCore import QUrl, Qt, QProcess, pyqtSlot, QTimer
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEngineSettings
from PyQt6.QtNetwork import QNetworkProxy, QSslCertificate, QSslConfiguration


class AggressiveSSLBypass:
    """
    Multiple approaches to bypass SSL certificate validation
    """

    @staticmethod
    def setup_application_arguments():
        """Set up command line arguments for QApplication"""
        ssl_args = [
            '--ignore-certificate-errors',
            '--ignore-ssl-errors',
            '--ignore-certificate-errors-spki-list',
            '--ignore-urlfetcher-cert-requests',
            '--disable-web-security',
            '--allow-running-insecure-content',
            '--disable-features=VizDisplayCompositor',
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu-sandbox',
            '--ignore-certificate-errors-policy',
            '--disable-extensions',
            '--allow-running-insecure-content',
            '--test-type'  # This is key - puts Chromium in test mode
        ]

        print("🔧 Adding SSL bypass arguments to sys.argv...")
        for arg in ssl_args:
            if arg not in sys.argv:
                sys.argv.append(arg)

        print(f"✅ Added {len(ssl_args)} SSL bypass arguments")
        return ssl_args

    @staticmethod
    def configure_web_profile(profile: QWebEngineProfile):
        """Configure web profile with aggressive SSL bypass settings"""
        print("🔧 Configuring web profile with aggressive SSL bypass...")

        # Disable cache
        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.NoCache)

        # Set permissive user agent
        profile.setHttpUserAgent("WebCapture/1.0 (SSL-Bypass)")

        # Get settings and make them permissive
        settings = profile.settings()

        # Enable everything that might help
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)

        print("✅ Web profile configured with aggressive settings")
        return profile


class CertificateHandler:
    """Enhanced certificate handler with multiple approaches"""

    def __init__(self, proxy_host="localhost", proxy_port=8080):
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.cert_dir = Path.home() / ".mitmproxy"
        self.cert_file = self.cert_dir / "mitmproxy-ca-cert.pem"

    def get_mitmproxy_cert_url(self):
        return f"http://{self.proxy_host}:{self.proxy_port}/cert/pem"

    def download_certificate(self):
        """Download certificate with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"📥 Downloading certificate (attempt {attempt + 1}/{max_retries})...")

                proxies = {
                    'http': f'http://{self.proxy_host}:{self.proxy_port}',
                    'https': f'http://{self.proxy_host}:{self.proxy_port}'
                }

                response = requests.get(
                    self.get_mitmproxy_cert_url(),
                    proxies=proxies,
                    timeout=15,
                    verify=False
                )
                response.raise_for_status()

                self.cert_dir.mkdir(parents=True, exist_ok=True)

                with open(self.cert_file, 'wb') as f:
                    f.write(response.content)

                print(f"✅ Certificate downloaded: {self.cert_file}")
                return True

            except Exception as e:
                print(f"❌ Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)  # Wait before retry

        return False


class SuperBypassWebView(QWebEngineView):
    """WebView with maximum SSL bypass configuration"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_bypass_profile()

    def setup_bypass_profile(self):
        """Set up a profile with maximum SSL bypass"""
        try:
            print("🚀 Setting up super bypass web profile...")

            # Create a custom profile
            self.bypass_profile = QWebEngineProfile("SuperBypass", self)

            # Apply aggressive SSL bypass configuration
            AggressiveSSLBypass.configure_web_profile(self.bypass_profile)

            # Create page with bypass profile
            self.bypass_page = QWebEnginePage(self.bypass_profile, self)
            self.setPage(self.bypass_page)

            print("✅ Super bypass web view initialized")

        except Exception as e:
            print(f"❌ Error setting up bypass profile: {e}")

    def get_bypass_status(self):
        """Get bypass configuration status"""
        return "SSL: Super Bypass Active"


class WebCaptureBrowser(QMainWindow):
    def __init__(self, api_port=8000, debug_port=9222, proxy_port=8080):
        super().__init__()

        self.api_port = api_port
        self.debug_port = debug_port
        self.proxy_port = proxy_port
        self.current_url = f"http://localhost:{api_port}/docs"
        self.current_url = "https://www.google.com"
        self.fastapi_process = None
        self.cert_handler = None

        # Set window properties
        self.setWindowTitle("Web Content Capture (SSL Bypass)")
        self.setGeometry(100, 100, 1200, 800)

        # Create UI
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.create_toolbar()
        self.setup_browser()

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Start services
        self.start_fastapi_server()
        QTimer.singleShot(2000, self.setup_proxy_configuration)

        atexit.register(self.cleanup)

    def create_toolbar(self):
        """Create navigation toolbar with SSL bypass status"""
        self.toolbar = QToolBar("Navigation")
        self.addToolBar(self.toolbar)

        # Navigation buttons
        back_action = QAction("Back", self)
        back_action.triggered.connect(lambda: self.web_view.back())
        self.toolbar.addAction(back_action)

        forward_action = QAction("Forward", self)
        forward_action.triggered.connect(lambda: self.web_view.forward())
        self.toolbar.addAction(forward_action)

        reload_action = QAction("Reload", self)
        reload_action.triggered.connect(lambda: self.web_view.reload())
        self.toolbar.addAction(reload_action)

        # URL entry
        self.url_edit = QLineEdit()
        self.url_edit.returnPressed.connect(self.navigate_to_url)
        self.toolbar.addWidget(self.url_edit)

        go_button = QPushButton("Go")
        go_button.clicked.connect(self.navigate_to_url)
        self.toolbar.addWidget(go_button)

        self.toolbar.addSeparator()

        # Status indicators
        self.proxy_status_button = QPushButton("Proxy: Connecting...")
        self.proxy_status_button.clicked.connect(self.show_proxy_status)
        self.toolbar.addWidget(self.proxy_status_button)

        self.ssl_status_button = QPushButton("SSL: Super Bypass")
        self.ssl_status_button.clicked.connect(self.show_ssl_status)
        self.ssl_status_button.setStyleSheet("background-color: #4CAF50; color: white;")
        self.toolbar.addWidget(self.ssl_status_button)

    def setup_browser(self):
        """Set up the super bypass web browser"""
        print("🚀 Setting up super bypass browser...")

        # Use the super bypass web view
        self.web_view = SuperBypassWebView(self)
        self.web_view.loadFinished.connect(self.on_load_finished)
        self.web_view.loadStarted.connect(lambda: self.status_bar.showMessage("Loading..."))

        self.layout.addWidget(self.web_view)

        # Initial URL loading
        QTimer.singleShot(4000, self.load_initial_url)

    def setup_proxy_configuration(self):
        """Set up proxy with enhanced error handling"""
        try:
            print(f"🔧 Setting up proxy: localhost:{self.proxy_port}")

            proxy = QNetworkProxy()
            proxy.setType(QNetworkProxy.ProxyType.HttpProxy)
            proxy.setHostName("localhost")
            proxy.setPort(self.proxy_port)
            QNetworkProxy.setApplicationProxy(proxy)

            self.proxy_status_button.setText("Proxy: ✅ Connected")
            self.status_bar.showMessage(f"Proxy active: localhost:{self.proxy_port}")

            # Set up certificate handler
            self.cert_handler = CertificateHandler("localhost", self.proxy_port)

            # Download certificate if needed
            if not self.cert_handler.cert_file.exists():
                QTimer.singleShot(1000, self.download_certificate)

        except Exception as e:
            print(f"❌ Proxy setup error: {e}")
            self.proxy_status_button.setText("Proxy: ❌ Error")

    def download_certificate(self):
        """Download certificate with user feedback"""
        try:
            self.status_bar.showMessage("Downloading mitmproxy certificate...")
            success = self.cert_handler.download_certificate()

            if success:
                self.status_bar.showMessage("✅ Certificate downloaded")
            else:
                self.status_bar.showMessage("⚠️ Certificate download failed")

        except Exception as e:
            print(f"❌ Certificate download error: {e}")

    def show_ssl_status(self):
        """Show detailed SSL bypass status"""
        status_text = f"""SSL Bypass Configuration:

🔧 Environment Variables: SET
   QTWEBENGINE_CHROMIUM_FLAGS with SSL bypass options
   QTWEBENGINE_DISABLE_SANDBOX=1

🔧 Command Line Arguments: APPLIED
   --ignore-certificate-errors
   --ignore-ssl-errors
   --disable-web-security
   --test-type (Chromium test mode)
   + 10 additional SSL bypass flags

🔧 Profile Configuration: ACTIVE
   Custom QWebEngineProfile with permissive settings
   AllowRunningInsecureContent enabled

Certificate File: {self.cert_handler.cert_file if self.cert_handler else 'Not configured'}

This is the most aggressive SSL bypass configuration possible.
If HTTPS sites still show certificate errors, the issue may be:
1. mitmproxy not running
2. Proxy not configured correctly
3. Network connectivity issues"""

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("SSL Bypass Status")
        msg.setText("Aggressive SSL Bypass Active")
        msg.setInformativeText(status_text)
        msg.exec()

    def show_proxy_status(self):
        """Show proxy configuration details"""
        if self.cert_handler:
            status_text = f"""Proxy Configuration:
Host: localhost
Port: {self.proxy_port}
Type: HTTP Proxy

Certificate: {self.cert_handler.cert_file}
Download URL: {self.cert_handler.get_mitmproxy_cert_url()}

SSL Bypass: Multiple layers active
- Environment variables
- Command line flags  
- Profile configuration"""
        else:
            status_text = "Proxy not configured"

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Proxy Status")
        msg.setText("Proxy Configuration")
        msg.setInformativeText(status_text)
        msg.exec()

    def load_initial_url(self):
        """Load initial URL"""
        self.web_view.load(QUrl(self.current_url))
        self.url_edit.setText(self.current_url)

    def navigate_to_url(self):
        """Navigate to URL"""
        url = self.url_edit.text()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        print(f"🌐 Navigating to: {url}")
        self.web_view.load(QUrl(url))
        self.current_url = url

    @pyqtSlot(bool)
    def on_load_finished(self, success):
        """Handle page load completion"""
        if success:
            self.status_bar.showMessage(f"✅ Loaded: {self.web_view.url().toString()}")
            self.url_edit.setText(self.web_view.url().toString())
        else:
            self.status_bar.showMessage("❌ Failed to load page")

    def start_fastapi_server(self):
        """Start FastAPI server"""
        try:
            server_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")
            python_executable = sys.executable

            if getattr(sys, 'frozen', False):
                def run_server():
                    import server
                    import uvicorn
                    uvicorn.run(server.app, host="127.0.0.1", port=self.api_port)

                server_thread = threading.Thread(target=run_server)
                server_thread.daemon = True
                server_thread.start()
            else:
                cmd = [python_executable, server_path, '--port', str(self.api_port)]
                self.fastapi_process = QProcess()
                self.fastapi_process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
                self.fastapi_process.readyReadStandardOutput.connect(self.handle_server_output)
                self.fastapi_process.start(python_executable, cmd[1:])

        except Exception as e:
            print(f"❌ FastAPI server error: {e}")

    def handle_server_output(self):
        """Handle FastAPI server output"""
        if self.fastapi_process:
            data = self.fastapi_process.readAllStandardOutput().data().decode()
            print(f"FastAPI: {data.strip()}")

    def cleanup(self):
        """Cleanup on exit"""
        if hasattr(self, 'fastapi_process') and self.fastapi_process:
            self.fastapi_process.terminate()
            self.fastapi_process.waitForFinished(1000)
            if self.fastapi_process.state() == QProcess.ProcessState.Running:
                self.fastapi_process.kill()


def main():
    # Parse arguments first
    parser = argparse.ArgumentParser(description="Web Content Capture with Aggressive SSL Bypass")
    parser.add_argument('--api-port', type=int, default=8000, help='FastAPI port')
    parser.add_argument('--debug-port', type=int, default=9222, help='Debug port')
    parser.add_argument('--proxy-port', type=int, default=8080, help='mitmproxy port')

    args, unknown = parser.parse_known_args()

    # Apply SSL bypass arguments
    AggressiveSSLBypass.setup_application_arguments()

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("Web Content Capture")
    app.setOrganizationName("Web Content Capture")

    print("🚀 Starting Web Content Capture with AGGRESSIVE SSL bypass...")

    browser = WebCaptureBrowser(api_port=args.api_port, debug_port=args.debug_port, proxy_port=args.proxy_port)
    browser.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()