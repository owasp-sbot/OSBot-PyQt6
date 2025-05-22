#!/usr/bin/env python3
import sys
import os
import signal
import subprocess
import time
import threading
import argparse
import atexit
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QToolBar, QLineEdit, QPushButton, \
    QStatusBar
from PyQt6.QtCore import QUrl, Qt, QProcess, pyqtSlot, QTimer
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile


class WebCaptureBrowser(QMainWindow):
    def __init__(self, api_port=8000, debug_port=9222):
        super().__init__()

        self.api_port = api_port
        self.debug_port = debug_port
        self.current_url = f"http://localhost:{api_port}/docs"
        self.fastapi_process = None

        # Set window properties
        self.setWindowTitle("Web Content Capture")
        self.setGeometry(100, 100, 1200, 800)

        # Set icon (replace with path to your icon)
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "app_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Create central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # Create toolbar
        self.create_toolbar()

        # Create web view
        self.setup_browser()

        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Start FastAPI server
        self.start_fastapi_server()

        # Set up cleanup on exit
        atexit.register(self.cleanup)

    def create_toolbar(self):
        """Create navigation toolbar"""
        self.toolbar = QToolBar("Navigation")
        self.addToolBar(self.toolbar)

        # Back button
        back_action = QAction("Back", self)
        back_action.triggered.connect(lambda: self.web_view.back())
        self.toolbar.addAction(back_action)

        # Forward button
        forward_action = QAction("Forward", self)
        forward_action.triggered.connect(lambda: self.web_view.forward())
        self.toolbar.addAction(forward_action)

        # Reload button
        reload_action = QAction("Reload", self)
        reload_action.triggered.connect(lambda: self.web_view.reload())
        self.toolbar.addAction(reload_action)

        # URL entry field
        self.url_edit = QLineEdit()
        self.url_edit.returnPressed.connect(self.navigate_to_url)
        self.toolbar.addWidget(self.url_edit)

        # Go button
        go_button = QPushButton("Go")
        go_button.clicked.connect(self.navigate_to_url)
        self.toolbar.addWidget(go_button)

    def setup_browser(self):
        """Set up the web browser component"""
        # Create web profile with custom settings
        self.web_profile = QWebEngineProfile("WebCapture", self)

        # Create web view with the custom profile
        self.web_view = QWebEngineView()
        self.web_view.loadFinished.connect(self.on_load_finished)
        self.web_view.loadStarted.connect(lambda: self.status_bar.showMessage("Loading..."))

        # Add web view to layout
        self.layout.addWidget(self.web_view)

        # Initial URL loading delayed to ensure server is up
        QTimer.singleShot(2000, self.load_initial_url)

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
            # Get the path to the server.py file
            server_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")

            # Start FastAPI server
            python_executable = sys.executable

            # Check if we're running in a bundled application
            if getattr(sys, 'frozen', False):
                # If we're in a PyInstaller bundle, import and run the server directly
                self.status_bar.showMessage(f"Starting FastAPI server on port {self.api_port} (bundled mode)...")

                # Start in a separate thread to avoid blocking the UI
                def run_server():
                    import server
                    import uvicorn
                    uvicorn.run(server.app, host="127.0.0.1", port=self.api_port)

                server_thread = threading.Thread(target=run_server)
                server_thread.daemon = True
                server_thread.start()
            else:
                # Regular development mode - start as subprocess
                cmd = [python_executable, server_path, '--port', str(self.api_port)]

                # Use QProcess for better integration with Qt
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

        # Update status bar with the latest server output
        lines = data.strip().split('\n')
        if lines:
            self.status_bar.showMessage(lines[-1])

    def cleanup(self):
        """Clean up resources on app exit"""
        if hasattr(self, 'fastapi_process') and self.fastapi_process and self.fastapi_process.state() == QProcess.ProcessState.Running:
            self.fastapi_process.terminate()
            # Give it a chance to terminate gracefully
            self.fastapi_process.waitForFinished(1000)
            if self.fastapi_process.state() == QProcess.ProcessState.Running:
                self.fastapi_process.kill()
            print("FastAPI server terminated")


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Web Content Capture Application")
    parser.add_argument('--api-port', type=int, default=8000, help='Port for FastAPI server')
    parser.add_argument('--debug-port', type=int, default=9222, help='Chrome debug port')
    args = parser.parse_args()

    # Set up signal handling for clean exit
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Create and run the application
    app = QApplication(sys.argv)
    app.setApplicationName("Web Content Capture")
    app.setOrganizationName("Web Content Capture")

    browser = WebCaptureBrowser(api_port=args.api_port, debug_port=args.debug_port)
    browser.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()