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
import json
from pathlib import Path

from osbot_utils.helpers.duration.decorators.capture_duration import capture_duration

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

from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, QToolBar, QLineEdit, QPushButton,
                             QStatusBar, QMessageBox, QTextEdit, QTabWidget, QHBoxLayout, QCheckBox, QLabel, QGroupBox,
                             QScrollArea)
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

    def __init__(self, port=8080, host="127.0.0.1", storage_dir=None, enable_replacement=True):
        super().__init__()
        self.port = port
        self.host = host
        self.storage_dir = storage_dir
        self.enable_replacement = enable_replacement
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
                verbose=True,
                enable_replacement=self.enable_replacement
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

    def reload_replacement_config(self):
        """Reload replacement configuration"""
        if self.proxy_server:
            self.proxy_server.reload_replacement_config()


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
    def __init__(self, api_port=8000, debug_port=9222, proxy_port=8080, enable_replacement=True):
        super().__init__()

        self.api_port = api_port
        self.debug_port = debug_port
        self.proxy_port = proxy_port
        self.enable_replacement = enable_replacement
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

        # Content Replacement tab
        self.replacement_tab = QWidget()
        self.replacement_layout = QVBoxLayout(self.replacement_tab)
        self.setup_replacement_tab()
        self.tab_widget.addTab(self.replacement_tab, "Content Replacement")

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

        # Quick navigation buttons
        dinis_button = QPushButton("Dinis Cruz site")
        dinis_button.clicked.connect(lambda: self.navigate_to_specific_url("https://docs.diniscruz.ai"))
        self.toolbar.addWidget(dinis_button)

        bbc_sports_button = QPushButton("BBC Sports")
        bbc_sports_button.clicked.connect(lambda: self.navigate_to_specific_url("https://www.bbc.co.uk/sport"))
        self.toolbar.addWidget(bbc_sports_button)

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

        # Content replacement status button
        replacement_status = "✅ Enabled" if self.enable_replacement else "❌ Disabled"
        self.replacement_status_button = QPushButton(f"Replacement: {replacement_status}")
        self.replacement_status_button.clicked.connect(self.show_replacement_status)
        style_color = "#4CAF50" if self.enable_replacement else "#f44336"
        self.replacement_status_button.setStyleSheet(f"background-color: {style_color}; color: white;")
        self.toolbar.addWidget(self.replacement_status_button)

    def navigate_to_specific_url(self, url):
        """Navigate to a specific URL"""
        print(f"🌐 Navigating to: {url}")
        self.web_view.load(QUrl(url))
        self.url_edit.setText(url)
        self.current_url = url

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

    def setup_replacement_tab(self):
        """Set up the content replacement configuration tab"""
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Configuration file info
        config_group = QGroupBox("Configuration")
        config_layout = QVBoxLayout(config_group)

        config_file_path = self.storage_dir / "replacements.json"
        config_info = QLabel(f"Configuration file: {config_file_path}")
        config_layout.addWidget(config_info)

        # Control buttons
        button_layout = QHBoxLayout()

        reload_config_button = QPushButton("Reload Configuration")
        reload_config_button.clicked.connect(self.reload_replacement_config)
        button_layout.addWidget(reload_config_button)

        view_config_button = QPushButton("View Configuration File")
        view_config_button.clicked.connect(self.view_replacement_config)
        button_layout.addWidget(view_config_button)

        edit_config_button = QPushButton("Edit Configuration File")
        edit_config_button.clicked.connect(self.edit_replacement_config)
        button_layout.addWidget(edit_config_button)

        config_layout.addLayout(button_layout)
        scroll_layout.addWidget(config_group)

        # Replacement rules display
        rules_group = QGroupBox("Replacement Rules")
        rules_layout = QVBoxLayout(rules_group)

        self.replacement_rules_display = QTextEdit()
        self.replacement_rules_display.setReadOnly(True)
        self.replacement_rules_display.setStyleSheet("font-family: monospace; font-size: 11px;")
        rules_layout.addWidget(self.replacement_rules_display)

        refresh_rules_button = QPushButton("Refresh Rules Display")
        refresh_rules_button.clicked.connect(self.refresh_replacement_rules_display)
        rules_layout.addWidget(refresh_rules_button)

        scroll_layout.addWidget(rules_group)

        # Statistics group
        stats_group = QGroupBox("Replacement Statistics")
        stats_layout = QVBoxLayout(stats_group)

        self.replacement_stats_display = QTextEdit()
        self.replacement_stats_display.setReadOnly(True)
        self.replacement_stats_display.setStyleSheet("font-family: monospace; font-size: 11px;")
        stats_layout.addWidget(self.replacement_stats_display)

        refresh_stats_button = QPushButton("Refresh Statistics")
        refresh_stats_button.clicked.connect(self.refresh_replacement_stats)
        stats_layout.addWidget(refresh_stats_button)

        scroll_layout.addWidget(stats_group)

        scroll_area.setWidget(scroll_widget)
        self.replacement_layout.addWidget(scroll_area)

        # Auto-refresh timer
        self.replacement_refresh_timer = QTimer()
        self.replacement_refresh_timer.timeout.connect(self.refresh_replacement_stats)
        self.replacement_refresh_timer.start(5000)  # Refresh every 5 seconds

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
                storage_dir=str(self.storage_dir),
                enable_replacement=self.enable_replacement
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

        if "starting" in message.lower():
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
                with capture_duration(action_name="load logs from disk") as duration:
                    capture_dirs = [d for d in self.storage_dir.iterdir() if d.is_dir()]
                    log_content += f"Total Captures: {len(capture_dirs)}\n\n"

                    # Sort by actual timestamp from metadata
                    capture_items = []
                    for capture_dir in capture_dirs:
                        metadata_file = capture_dir / "metadata.json"
                        if metadata_file.exists():
                            try:
                                with open(metadata_file, 'r') as f:
                                    metadata = json.load(f)
                                timestamp = metadata.get("timestamp", "")
                                capture_items.append((timestamp, capture_dir, metadata))
                            except:
                                # If we can't read metadata, use folder name as fallback
                                capture_items.append(("", capture_dir, None))

                log_content += f"Captures loaded in : {duration.seconds}\n\n"
                # Sort by timestamp (most recent first) and take last 50
                capture_items.sort(key=lambda x: x[0], reverse=True)

                for timestamp, capture_dir, metadata in capture_items[:50]:
                    if metadata:
                        url = metadata.get("request", {}).get("url", "Unknown")
                        status = metadata.get("response", {}).get("status_code", "Unknown")
                        content_modified = metadata.get("response", {}).get("content_modified", False)
                        modification_indicator = "🔄" if content_modified else "📡"

                        log_content += f"{modification_indicator} [{timestamp}] {status} - {url}\n"
                    else:
                        log_content += f"[Error reading {capture_dir.name}]\n"
                # # Show recent captures
                # for capture_dir in sorted(capture_dirs, reverse=True)[:50]:
                #     metadata_file = capture_dir / "metadata.json"
                #     if metadata_file.exists():
                #         try:
                #             import json
                #             with open(metadata_file, 'r') as f:
                #                 metadata = json.load(f)
                #
                #             url = metadata.get("request", {}).get("url", "Unknown")
                #             status = metadata.get("response", {}).get("status_code", "Unknown")
                #             timestamp = metadata.get("timestamp", "Unknown")
                #             content_modified = metadata.get("response", {}).get("content_modified", False)
                #             modification_indicator = "🔄" if content_modified else "📡"
                #
                #             log_content += f"{modification_indicator} [{timestamp}] {status} - {url}\n"
                #
                #         except Exception as e:
                #             log_content += f"[Error reading {capture_dir.name}]: {e}\n"

            else:
                log_content += "No captures found.\n"

            self.capture_log.setPlainText(log_content)

        except Exception as e:
            self.capture_log.setPlainText(f"Error refreshing log: {e}")

    def reload_replacement_config(self):
        """Reload replacement configuration"""
        if self.mitmproxy_thread:
            self.mitmproxy_thread.reload_replacement_config()
            self.refresh_replacement_rules_display()
            QMessageBox.information(self, "Configuration Reloaded", "Replacement configuration has been reloaded.")

    def view_replacement_config(self):
        """View the replacement configuration file"""
        config_file = self.storage_dir / "replacements.json"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_content = f.read()

                dialog = QMessageBox(self)
                dialog.setIcon(QMessageBox.Icon.Information)
                dialog.setWindowTitle("Replacement Configuration")
                dialog.setText("Configuration File Content:")
                dialog.setDetailedText(config_content)
                dialog.exec()

            except Exception as e:
                QMessageBox.warning(self, "Error", f"Error reading configuration file: {e}")
        else:
            QMessageBox.information(self, "No Configuration",
                                    "Configuration file does not exist yet. It will be created when needed.")

    def edit_replacement_config(self):
        """Open configuration file in system editor"""
        config_file = self.storage_dir / "replacements.json"
        try:
            import subprocess
            import platform

            if platform.system() == "Windows":
                subprocess.run(["notepad", str(config_file)], check=False)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", "-t", str(config_file)], check=False)
            else:  # Linux
                subprocess.run(["xdg-open", str(config_file)], check=False)

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error opening configuration file: {e}")

    def refresh_replacement_rules_display(self):
        """Refresh the replacement rules display"""
        config_file = self.storage_dir / "replacements.json"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                rules_text = "Replacement Rules:\n"
                rules_text += "=" * 50 + "\n\n"

                replacements = config.get("replacements", [])
                for i, rule in enumerate(replacements, 1):
                    enabled = rule.get("enabled", True)
                    status_icon = "✅" if enabled else "❌"
                    rules_text += f"{i}. {status_icon} {rule.get('name', 'Unnamed Rule')}\n"
                    rules_text += f"   Pattern: {rule.get('pattern', 'N/A')}\n"
                    rules_text += f"   Replacement: {rule.get('replacement', 'N/A')}\n"
                    rules_text += f"   Content Types: {rule.get('content_types', ['any'])}\n"
                    rules_text += f"   Description: {rule.get('description', 'No description')}\n\n"

                if not replacements:
                    rules_text += "No replacement rules defined.\n"

                self.replacement_rules_display.setPlainText(rules_text)

            except Exception as e:
                self.replacement_rules_display.setPlainText(f"Error reading rules: {e}")
        else:
            self.replacement_rules_display.setPlainText("Configuration file does not exist yet.")

    def refresh_replacement_stats(self):
        """Refresh replacement statistics display"""
        try:
            # This would need to be implemented to get stats from the mitmproxy thread
            stats_text = "Replacement Statistics:\n"
            stats_text += "=" * 50 + "\n\n"
            stats_text += "📊 Statistics will be available once the proxy processes some requests.\n"
            stats_text += f"🔄 Content replacement: {'Enabled' if self.enable_replacement else 'Disabled'}\n"
            stats_text += f"📁 Storage directory: {self.storage_dir}\n"

            if self.storage_dir.exists():
                config_file = self.storage_dir / "replacements.json"
                if config_file.exists():
                    try:
                        with open(config_file, 'r') as f:
                            config = json.load(f)

                        stats = config.get("stats", {})
                        if stats:
                            stats_text += f"\n📈 Total processed: {stats.get('total_processed', 0)}\n"
                            stats_text += f"🔄 Total replaced: {stats.get('total_replaced', 0)}\n"
                            stats_text += f"📅 Last updated: {stats.get('last_updated', 'Never')}\n"
                    except:
                        pass

            self.replacement_stats_display.setPlainText(stats_text)

        except Exception as e:
            self.replacement_stats_display.setPlainText(f"Error getting stats: {e}")

    def show_proxy_status(self):
        """Show proxy status dialog"""
        status_text = f"""Integrated Mitmproxy Status:

Host: localhost
Port: {self.proxy_port}
Storage Directory: {self.storage_dir}
Thread Running: {self.mitmproxy_thread.isRunning() if self.mitmproxy_thread else False}
Content Replacement: {'✅ Enabled' if self.enable_replacement else '❌ Disabled'}

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

    def show_replacement_status(self):
        """Show content replacement status"""
        status_text = f"""Content Replacement Status:

Status: {'✅ Enabled' if self.enable_replacement else '❌ Disabled'}
Configuration File: {self.storage_dir / 'replacements.json'}

Content replacement allows you to modify web content
in real-time as it passes through the proxy.

Features:
- Regex-based pattern matching
- Support for multiple content types
- Configurable replacement rules
- Statistics tracking

Check the 'Content Replacement' tab to configure rules."""

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Content Replacement Status")
        msg.setText("Content Replacement")
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

        # Stop replacement refresh timer
        if hasattr(self, 'replacement_refresh_timer'):
            self.replacement_refresh_timer.stop()

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
    parser.add_argument('--no-replacement', action='store_true', help='Disable content replacement')

    args, unknown = parser.parse_known_args()

    # Apply SSL bypass arguments
    AggressiveSSLBypass.setup_application_arguments()

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("Web Content Capture")
    app.setOrganizationName("Web Content Capture")

    enable_replacement = not args.no_replacement

    print("🚀 Starting Web Content Capture with INTEGRATED mitmproxy...")
    print(f"🔄 Content replacement: {'✅ Enabled' if enable_replacement else '❌ Disabled'}")

    browser = WebCaptureBrowser(
        api_port=args.api_port,
        debug_port=args.debug_port,
        proxy_port=args.proxy_port,
        enable_replacement=enable_replacement
    )
    browser.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()