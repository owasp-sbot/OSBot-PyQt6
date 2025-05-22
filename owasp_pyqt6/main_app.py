#!/usr/bin/env python3
"""
Web Content Capture with integrated local mitmproxy
This version starts mitmproxy locally within the Python application
"""

import os
import sys
import signal
import subprocess
import time
import threading
import argparse
import atexit
import requests
import tempfile
import asyncio
from pathlib import Path

# Import the local mitmproxy implementation
from start_mitmproxy import LocalMitmproxy, ContentCaptureAddon


# Set environment variables BEFORE any Qt imports
def setup_chromium_environment():
    """Set environment variables that affect Chromium/QtWebEngine SSL behavior"""
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

    return chromium_env_vars


# Apply environment setup IMMEDIATELY
setup_chromium_environment()

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QToolBar, QLineEdit, QPushButton, \
    QStatusBar, QMessageBox, QTextEdit, QTabWidget
from PyQt6.QtCore import QUrl, Qt, QProcess, pyqtSlot, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEngineSettings
from PyQt6.QtNetwork import QNetworkProxy


class MitmproxyThread(QThread):
    """
    Thread to run mitmproxy server without blocking the UI
    """
    status_update = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, port=8080, host="127.0.0.1", storage_dir=None):
        super().__init__()
        self.port = port
        self.host = host
        self.storage_dir = storage_dir
        self.proxy_server = None
        self.should_stop = False

    def run(self):
        """Run the mitmproxy server in this thread"""
        try:
            self.status_update.emit(f"Starting mitmproxy on {self.host}:{self.port}...")

            # Create the proxy server
            self.proxy_server = LocalMitmproxy(
                port=self.port,
                host=self.host,
                storage_dir=self.storage_dir,
                verbose=True
            )

            self.status_update.emit("Mitmproxy server starting...")

            # Run the server (this will block)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.proxy_server.start())

        except Exception as e:
            self.error_occurred.emit(f"Mitmproxy error: {str(e)}")

    def stop_proxy(self):
        """Stop the proxy server"""
        self.should_stop = True
        if self.proxy_server:
            self.proxy_server.stop()
        self.quit()
        self.wait()


class AggressiveSSLBypass:
    """SSL bypass configuration"""

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
            '--test-type'
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

        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.NoCache)
        profile.setHttpUserAgent("WebCapture/1.0 (SSL-Bypass)")

        settings = profile.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)

        print("✅ Web profile configured with aggressive settings")
        return profile


class SuperBypassWebView(QWebEngineView):
    """WebView with maximum SSL bypass configuration"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_bypass_profile()

    def setup_bypass_profile(self):
        """Set up a profile with maximum SSL bypass"""
        try:
            print("🚀 Setting up super bypass web profile...")

            self.bypass_profile = QWebEngineProfile("SuperBypass", self)
            AggressiveSSLBypass.configure_web_profile(self.bypass_profile)

            self.bypass_page = QWebEnginePage(self.bypass_profile, self)
            self.setPage(self.bypass_page)

            print("✅ Super bypass web view initialized")

        except Exception as e:
            print(f"❌ Error setting up bypass profile: {e}")


class WebCaptureBrowser(QMainWindow):
    def __init__(self, api_port=8000, debug_port=9222, proxy_port=8080):
        super().__init__()

        self.api_port = api_port
        self.debug_port = debug_port
        self.proxy_port = proxy_port
        self.current_url = f"http://localhost:{api_port}/docs"
        self.current_url = f"https://docs.diniscruz.ai"
        self.fastapi_process = None
        self.mitmproxy_thread = None
        self.storage_dir = Path("./captures")

        # Set window properties
        self.setWindowTitle("Web Content Capture (Integrated Mitmproxy)")
        self.setGeometry(100, 100, 1400, 900)

        # Create UI
        self.setup_ui()

        # Start services
        self.start_fastapi_server()
        self.start_mitmproxy_server()

        # Set up proxy configuration after mitmproxy starts
        QTimer.singleShot(3000, self.setup_proxy_configuration)

        atexit.register(self.cleanup)

    def setup_ui(self):
        """Set up the user interface with tabs"""
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.create_toolbar()

        # Create tab widget
        self.tab_widget = QTabWidget()
        self.layout.addWidget(self.tab_widget)

        # Browser tab
        self.browser_tab = QWidget()
        self.browser_layout = QVBoxLayout(self.browser_tab)
        self.setup_browser()
        self.tab_widget.addTab(self.browser_tab, "Browser")

        # Capture log tab
        self.log_tab = QWidget()
        self.log_layout = QVBoxLayout(self.log_tab)
        self.setup_capture_log()
        self.tab_widget.addTab(self.log_tab, "Capture Log")

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def create_toolbar(self):
        """Create navigation toolbar"""
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
        self.proxy_status_button = QPushButton("Proxy: Starting...")
        self.proxy_status_button.clicked.connect(self.show_proxy_status)
        self.toolbar.addWidget(self.proxy_status_button)

        self.ssl_status_button = QPushButton("SSL: Super Bypass")
        self.ssl_status_button.clicked.connect(self.show_ssl_status)
        self.ssl_status_button.setStyleSheet("background-color: #4CAF50; color: white;")
        self.toolbar.addWidget(self.ssl_status_button)

        self.capture_status_button = QPushButton("Capture: Ready")
        self.capture_status_button.clicked.connect(self.show_capture_status)
        self.toolbar.addWidget(self.capture_status_button)

    def setup_browser(self):
        """Set up the browser component"""
        print("🚀 Setting up integrated browser...")

        self.web_view = SuperBypassWebView(self)
        self.web_view.loadFinished.connect(self.on_load_finished)
        self.web_view.loadStarted.connect(lambda: self.status_bar.showMessage("Loading..."))

        self.browser_layout.addWidget(self.web_view)

        # Initial URL loading
        QTimer.singleShot(5000, self.load_initial_url)

    def setup_capture_log(self):
        """Set up the capture log display"""
        self.capture_log = QTextEdit()
        self.capture_log.setReadOnly(True)
        self.capture_log.setStyleSheet("font-family: monospace; font-size: 12px;")
        self.log_layout.addWidget(self.capture_log)

        # Add refresh button
        refresh_button = QPushButton("Refresh Capture Log")
        refresh_button.clicked.connect(self.refresh_capture_log)
        self.log_layout.addWidget(refresh_button)

    def start_mitmproxy_server(self):
        """Start the integrated mitmproxy server"""
        try:
            print(f"🚀 Starting integrated mitmproxy server on port {self.proxy_port}...")

            # Create storage directory
            self.storage_dir.mkdir(exist_ok=True)

            # Create and start mitmproxy thread
            self.mitmproxy_thread = MitmproxyThread(
                port=self.proxy_port,
                host="127.0.0.1",
                storage_dir=str(self.storage_dir)
            )

            # Connect signals
            self.mitmproxy_thread.status_update.connect(self.on_mitmproxy_status)
            self.mitmproxy_thread.error_occurred.connect(self.on_mitmproxy_error)

            # Start the thread
            self.mitmproxy_thread.start()

            self.proxy_status_button.setText("Proxy: Starting...")

        except Exception as e:
            print(f"❌ Error starting mitmproxy: {e}")
            self.proxy_status_button.setText("Proxy: ❌ Error")

    def on_mitmproxy_status(self, message):
        """Handle mitmproxy status updates"""
        print(f"📡 Mitmproxy: {message}")
        self.status_bar.showMessage(message)

        if "listening" in message.lower():
            self.proxy_status_button.setText("Proxy: ✅ Running")
            self.capture_status_button.setText("Capture: ✅ Active")

    def on_mitmproxy_error(self, error_message):
        """Handle mitmproxy errors"""
        print(f"❌ Mitmproxy error: {error_message}")
        self.proxy_status_button.setText("Proxy: ❌ Error")
        self.status_bar.showMessage(f"Mitmproxy error: {error_message}")

    def setup_proxy_configuration(self):
        """Set up proxy configuration"""
        try:
            print(f"🔧 Setting up proxy: localhost:{self.proxy_port}")

            proxy = QNetworkProxy()
            proxy.setType(QNetworkProxy.ProxyType.HttpProxy)
            proxy.setHostName("localhost")
            proxy.setPort(self.proxy_port)
            QNetworkProxy.setApplicationProxy(proxy)

            self.status_bar.showMessage(f"Proxy configured: localhost:{self.proxy_port}")

        except Exception as e:
            print(f"❌ Proxy setup error: {e}")

    def refresh_capture_log(self):
        """Refresh the capture log display"""
        try:
            # Read capture files from storage directory
            log_content = f"Capture Storage Directory: {self.storage_dir}\n"
            log_content += "=" * 50 + "\n\n"

            if self.storage_dir.exists():
                capture_dirs = [d for d in self.storage_dir.iterdir() if d.is_dir()]
                log_content += f"Total Captures: {len(capture_dirs)}\n\n"

                # Show recent captures
                for capture_dir in sorted(capture_dirs, reverse=True)[:10]:
                    metadata_file = capture_dir / "metadata.json"
                    if metadata_file.exists():
                        try:
                            import json
                            with open(metadata_file, 'r') as f:
                                metadata = json.load(f)

                            url = metadata.get("request", {}).get("url", "Unknown")
                            status = metadata.get("response", {}).get("status_code", "Unknown")
                            timestamp = metadata.get("timestamp", "Unknown")

                            log_content += f"[{timestamp}] {status} - {url}\n"

                        except Exception as e:
                            log_content += f"[Error reading {capture_dir.name}]: {e}\n"

            else:
                log_content += "No captures found.\n"

            self.capture_log.setPlainText(log_content)

        except Exception as e:
            self.capture_log.setPlainText(f"Error refreshing log: {e}")

    def show_proxy_status(self):
        """Show proxy status dialog"""
        status_text = f"""Integrated Mitmproxy Status:

Host: localhost
Port: {self.proxy_port}
Storage Directory: {self.storage_dir}
Thread Running: {self.mitmproxy_thread.isRunning() if self.mitmproxy_thread else False}

This is a local Python mitmproxy instance running within the application.
All web traffic is intercepted and saved to the storage directory.

SSL Bypass: Multiple layers active
Content Capture: Automatic for all HTTP/HTTPS requests"""

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Integrated Proxy Status")
        msg.setText("Local Mitmproxy Server")
        msg.setInformativeText(status_text)
        msg.exec()

    def show_ssl_status(self):
        """Show SSL configuration status"""
        status_text = """SSL Bypass Configuration:

🔧 Environment Variables: SET
🔧 Command Line Arguments: APPLIED  
🔧 Profile Configuration: ACTIVE

This aggressive SSL bypass allows HTTPS sites to load
through the mitmproxy without certificate errors.

All content is captured automatically."""

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("SSL Bypass Status")
        msg.setText("Aggressive SSL Bypass Active")
        msg.setInformativeText(status_text)
        msg.exec()

    def show_capture_status(self):
        """Show content capture status"""
        if self.storage_dir.exists():
            capture_count = len([d for d in self.storage_dir.iterdir() if d.is_dir()])
        else:
            capture_count = 0

        status_text = f"""Content Capture Status:

Storage Directory: {self.storage_dir}
Total Captures: {capture_count}
Capture Format: JSON metadata + content files

Each captured request/response is stored with:
- metadata.json (URL, headers, timestamps)
- response.html/json/txt/bin (actual content)
- request.bin (if request has body)

Content is automatically captured for all traffic
passing through the integrated mitmproxy."""

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Content Capture Status")
        msg.setText("Automatic Content Capture Active")
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
            # Auto-refresh capture log when page loads
            QTimer.singleShot(1000, self.refresh_capture_log)
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
        print("🧹 Cleaning up...")

        # Stop mitmproxy
        if self.mitmproxy_thread:
            self.mitmproxy_thread.stop_proxy()

        # Stop FastAPI
        if hasattr(self, 'fastapi_process') and self.fastapi_process:
            self.fastapi_process.terminate()
            self.fastapi_process.waitForFinished(1000)
            if self.fastapi_process.state() == QProcess.ProcessState.Running:
                self.fastapi_process.kill()


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description="Web Content Capture with Integrated Mitmproxy")
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

    print("🚀 Starting Web Content Capture with INTEGRATED mitmproxy...")

    browser = WebCaptureBrowser(api_port=args.api_port, debug_port=args.debug_port, proxy_port=args.proxy_port)
    browser.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()