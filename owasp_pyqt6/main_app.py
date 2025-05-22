#!/usr/bin/env python3
import sys
import os
import signal
import subprocess
import time
import threading
import argparse
import atexit
import requests
import tempfile
from pathlib import Path

# SSL bypass arguments - will be applied before QApplication creation
SSL_BYPASS_ARGS = [
    '--ignore-certificate-errors',
    '--ignore-ssl-errors',
    '--ignore-certificate-errors-spki-list',
    '--ignore-urlfetcher-cert-requests',
    '--disable-web-security',
    '--allow-running-insecure-content',
    '--disable-features=VizDisplayCompositor'
]


def apply_ssl_bypass_args():
    """Apply SSL bypass arguments to sys.argv for QtWebEngine"""
    print("🔧 Applying QtWebEngine SSL bypass arguments...")

    for arg in SSL_BYPASS_ARGS:
        if arg not in sys.argv:
            sys.argv.append(arg)

    print(f"✅ Applied {len(SSL_BYPASS_ARGS)} SSL bypass arguments")
    return SSL_BYPASS_ARGS


from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QToolBar, QLineEdit, QPushButton, \
    QStatusBar, QMessageBox
from PyQt6.QtCore import QUrl, Qt, QProcess, pyqtSlot, QTimer
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PyQt6.QtNetwork import QNetworkProxy, QSslCertificate, QSslConfiguration


class SelfContainedSSLHandler:
    """Handles SSL certificates entirely within the application"""

    def __init__(self, cert_path=None):
        self.cert_path = cert_path or (Path.home() / ".mitmproxy" / "mitmproxy-ca-cert.pem")
        self.ssl_config = None
        self.ca_certificates = []

    def load_mitmproxy_certificate(self):
        """Load the mitmproxy CA certificate"""
        try:
            if not self.cert_path.exists():
                print(f"❌ Certificate file not found: {self.cert_path}")
                return None

            with open(self.cert_path, 'rb') as f:
                cert_data = f.read()

            cert = QSslCertificate(cert_data)

            if cert.isNull():
                print("❌ Failed to create SSL certificate from PEM data")
                return None

            print(f"✅ Loaded certificate: {cert.subjectInfo(QSslCertificate.SubjectInfo.CommonName)}")
            return cert

        except Exception as e:
            print(f"❌ Error loading certificate: {e}")
            return None

    def create_ssl_configuration(self):
        """Create SSL configuration that trusts our mitmproxy certificate"""
        try:
            mitm_cert = self.load_mitmproxy_certificate()
            if not mitm_cert:
                return None

            ssl_config = QSslConfiguration.defaultConfiguration()
            ca_certs = ssl_config.caCertificates()
            ca_certs.append(mitm_cert)

            ssl_config.setCaCertificates(ca_certs)

            self.ssl_config = ssl_config
            self.ca_certificates = ca_certs

            print(f"✅ SSL configuration created with {len(ca_certs)} CA certificates")
            return ssl_config

        except Exception as e:
            print(f"❌ Error creating SSL configuration: {e}")
            return None

    def apply_global_ssl_config(self):
        """Apply SSL configuration globally"""
        try:
            ssl_config = self.create_ssl_configuration()
            if ssl_config:
                QSslConfiguration.setDefaultConfiguration(ssl_config)
                print("✅ Global SSL configuration applied")
                return True
            return False
        except Exception as e:
            print(f"❌ Error applying global SSL configuration: {e}")
            return False


class CertificateHandler:
    """Handles mitmproxy certificate download and management"""

    def __init__(self, proxy_host="localhost", proxy_port=8080):
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.cert_dir = Path.home() / ".mitmproxy"
        self.cert_file = self.cert_dir / "mitmproxy-ca-cert.pem"

    def get_mitmproxy_cert_url(self):
        """Get the URL to download mitmproxy certificate"""
        return f"http://{self.proxy_host}:{self.proxy_port}/cert/pem"

    def download_certificate(self):
        """Download the mitmproxy CA certificate"""
        try:
            print(f"Downloading mitmproxy certificate from {self.get_mitmproxy_cert_url()}")

            proxies = {
                'http': f'http://{self.proxy_host}:{self.proxy_port}',
                'https': f'http://{self.proxy_host}:{self.proxy_port}'
            }

            response = requests.get(
                self.get_mitmproxy_cert_url(),
                proxies=proxies,
                timeout=10,
                verify=False
            )
            response.raise_for_status()

            self.cert_dir.mkdir(parents=True, exist_ok=True)

            with open(self.cert_file, 'wb') as f:
                f.write(response.content)

            print(f"Certificate saved to: {self.cert_file}")
            return True

        except Exception as e:
            print(f"Error downloading certificate: {e}")
            return False


class SSLAwareWebView(QWebEngineView):
    """Custom WebView with built-in SSL certificate handling"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ssl_handler = None
        self.custom_profile = None
        self.setup_ssl_handling()

    def setup_ssl_handling(self):
        """Set up SSL handling for this web view"""
        try:
            # Create custom profile
            self.custom_profile = QWebEngineProfile("WebCapture", self)
            self.custom_profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.NoCache)
            self.custom_profile.setHttpUserAgent("WebCapture/1.0")

            # Set up SSL handler
            self.ssl_handler = SelfContainedSSLHandler()

            # Apply SSL configuration globally (affects all QtWebEngine instances)
            self.ssl_handler.apply_global_ssl_config()

            # Create page with custom profile
            page = QWebEnginePage(self.custom_profile, self)
            self.setPage(page)

            print("✅ SSL-aware WebView initialized")

        except Exception as e:
            print(f"❌ Error setting up SSL handling: {e}")

    def get_ssl_status(self):
        """Get the current SSL configuration status"""
        if self.ssl_handler and self.ssl_handler.ssl_config:
            ca_count = len(self.ssl_handler.ca_certificates)
            return f"SSL: {ca_count} CAs loaded"
        else:
            return "SSL: Command-line bypass"


class WebCaptureBrowser(QMainWindow):
    def __init__(self, api_port=8000, debug_port=9222, proxy_port=8080):
        super().__init__()

        self.api_port = api_port
        self.debug_port = debug_port
        self.proxy_port = proxy_port
        self.current_url = f"http://localhost:{api_port}/docs"
        self.fastapi_process = None
        self.cert_handler = None

        # Set window properties
        self.setWindowTitle("Web Content Capture")
        self.setGeometry(100, 100, 1200, 800)

        # Set icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "app_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Create central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # Create toolbar
        self.create_toolbar()

        # Create web view with SSL handling
        self.setup_browser()

        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Start FastAPI server
        self.start_fastapi_server()

        # Set up proxy configuration (with delay to ensure proxy is ready)
        QTimer.singleShot(3000, self.setup_proxy_configuration)

        # Set up cleanup on exit
        atexit.register(self.cleanup)

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

        # Separator
        self.toolbar.addSeparator()

        # Status buttons
        self.proxy_status_button = QPushButton("Proxy: Connecting...")
        self.proxy_status_button.clicked.connect(self.show_proxy_status)
        self.toolbar.addWidget(self.proxy_status_button)

        self.ssl_status_button = QPushButton("SSL: Initializing...")
        self.ssl_status_button.clicked.connect(self.show_ssl_status)
        self.toolbar.addWidget(self.ssl_status_button)

    def setup_browser(self):
        """Set up the web browser component with SSL handling"""
        print("🔧 Setting up SSL-aware browser...")

        # Use SSL-aware web view
        self.web_view = SSLAwareWebView(self)
        self.web_view.loadFinished.connect(self.on_load_finished)
        self.web_view.loadStarted.connect(lambda: self.status_bar.showMessage("Loading..."))

        # Add web view to layout
        self.layout.addWidget(self.web_view)

        # Update SSL status
        self.ssl_status_button.setText(self.web_view.get_ssl_status())

        # Initial URL loading delayed to ensure server is up
        QTimer.singleShot(4000, self.load_initial_url)

    def setup_proxy_configuration(self):
        """Set up proxy configuration"""
        try:
            print(f"Setting up proxy configuration for port {self.proxy_port}")

            # Set up the proxy
            proxy = QNetworkProxy()
            proxy.setType(QNetworkProxy.ProxyType.HttpProxy)
            proxy.setHostName("localhost")
            proxy.setPort(self.proxy_port)
            QNetworkProxy.setApplicationProxy(proxy)

            self.proxy_status_button.setText("Proxy: ✅ Connected")
            self.status_bar.showMessage(f"Proxy configured: localhost:{self.proxy_port}")

            # Set up certificate handler
            self.cert_handler = CertificateHandler("localhost", self.proxy_port)

            # Try to download certificate if needed
            if not self.cert_handler.cert_file.exists():
                QTimer.singleShot(1000, self.download_certificate)
            else:
                print(f"✅ Certificate already exists: {self.cert_handler.cert_file}")

        except Exception as e:
            print(f"Error setting up proxy: {e}")
            self.proxy_status_button.setText("Proxy: ❌ Error")
            self.status_bar.showMessage(f"Proxy setup failed: {e}")

    def download_certificate(self):
        """Download the mitmproxy certificate"""
        try:
            print("Attempting to download mitmproxy certificate...")
            success = self.cert_handler.download_certificate()

            if success:
                self.status_bar.showMessage("Certificate downloaded successfully")
                print("✅ Certificate download completed")

                # Reload SSL configuration with new certificate
                if hasattr(self.web_view, 'ssl_handler'):
                    self.web_view.ssl_handler.apply_global_ssl_config()
                    self.ssl_status_button.setText(self.web_view.get_ssl_status())
            else:
                self.status_bar.showMessage("Certificate download failed")
                print("❌ Certificate download failed")

        except Exception as e:
            print(f"Error during certificate download: {e}")
            self.status_bar.showMessage(f"Certificate error: {e}")

    def show_ssl_status(self):
        """Show SSL configuration status"""
        if hasattr(self.web_view, 'ssl_handler') and self.web_view.ssl_handler:
            handler = self.web_view.ssl_handler
            cert_exists = handler.cert_path.exists()
            config_loaded = handler.ssl_config is not None

            status_text = f"""SSL Configuration Status:
Certificate File: {handler.cert_path}
Certificate Exists: {cert_exists}
SSL Config Loaded: {config_loaded}
CA Certificates: {len(handler.ca_certificates) if handler.ca_certificates else 0}

SSL Bypass Method: Command-line arguments
QtWebEngine will ignore certificate errors for HTTPS sites.

This is a self-contained solution that doesn't modify your system."""
        else:
            status_text = "SSL Status: Command-line bypass active"

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("SSL Status")
        msg.setText("SSL Configuration Details")
        msg.setInformativeText(status_text)
        msg.exec()

    def show_proxy_status(self):
        """Show detailed proxy status information"""
        if self.cert_handler:
            cert_exists = self.cert_handler.cert_file.exists()
            status_text = f"""Proxy Status:
Host: localhost
Port: {self.proxy_port}
Certificate File: {self.cert_handler.cert_file}
Certificate Exists: {cert_exists}

Certificate Download URL:
{self.cert_handler.get_mitmproxy_cert_url()}

Self-contained SSL: ✅ Active
No system modifications required."""
        else:
            status_text = "Proxy not configured"

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Proxy Status")
        msg.setText("Proxy Configuration Details")
        msg.setInformativeText(status_text)
        msg.exec()

    def load_initial_url(self):
        """Load the initial URL (FastAPI docs)"""
        self.web_view.load(QUrl(self.current_url))
        self.url_edit.setText(self.current_url)

    def navigate_to_url(self):
        """Navigate to URL entered in the URL bar"""
        url = self.url_edit.text()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        self.web_view.load(QUrl(url))
        self.current_url = url

    @pyqtSlot(bool)
    def on_load_finished(self, success):
        """Handle page load completion"""
        if success:
            self.status_bar.showMessage(f"Loaded: {self.web_view.url().toString()}")
            self.url_edit.setText(self.web_view.url().toString())
        else:
            self.status_bar.showMessage("Failed to load page")

    def start_fastapi_server(self):
        """Start the FastAPI server as a subprocess"""
        try:
            server_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")
            python_executable = sys.executable

            if getattr(sys, 'frozen', False):
                self.status_bar.showMessage(f"Starting FastAPI server on port {self.api_port} (bundled mode)...")

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

                self.status_bar.showMessage(f"Starting FastAPI server on port {self.api_port}...")

        except Exception as e:
            self.status_bar.showMessage(f"Error starting FastAPI server: {str(e)}")
            print(f"Error starting FastAPI server: {str(e)}")

    def handle_server_output(self):
        """Handle output from the FastAPI server process"""
        data = self.fastapi_process.readAllStandardOutput().data().decode()
        print(f"FastAPI: {data.strip()}")

        lines = data.strip().split('\n')
        if lines:
            self.status_bar.showMessage(lines[-1])

    def cleanup(self):
        """Clean up resources on app exit"""
        if hasattr(self,
                   'fastapi_process') and self.fastapi_process and self.fastapi_process.state() == QProcess.ProcessState.Running:
            self.fastapi_process.terminate()
            self.fastapi_process.waitForFinished(1000)
            if self.fastapi_process.state() == QProcess.ProcessState.Running:
                self.fastapi_process.kill()
            print("FastAPI server terminated")


def main():
    # Parse command line arguments FIRST (before adding Qt args)
    parser = argparse.ArgumentParser(description="Web Content Capture Application")
    parser.add_argument('--api-port', type=int, default=8000, help='Port for FastAPI server')
    parser.add_argument('--debug-port', type=int, default=9222, help='Chrome debug port')
    parser.add_argument('--proxy-port', type=int, default=8080, help='mitmproxy port')

    # Parse only known arguments to avoid conflicts with Qt arguments
    args, unknown = parser.parse_known_args()

    # Now apply SSL bypass arguments for QtWebEngine
    apply_ssl_bypass_args()

    # Set up signal handling for clean exit
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Create and run the application
    app = QApplication(sys.argv)
    app.setApplicationName("Web Content Capture")
    app.setOrganizationName("Web Content Capture")

    print("🚀 Starting Web Content Capture with self-contained SSL handling...")

    browser = WebCaptureBrowser(api_port=args.api_port, debug_port=args.debug_port, proxy_port=args.proxy_port)
    browser.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()