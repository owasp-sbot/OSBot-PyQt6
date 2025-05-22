#!/usr/bin/env python3
"""
Local mitmproxy implementation to replace Docker instance
This runs mitmproxy directly in Python with custom addons for content capture
"""

import sys
import asyncio
import threading
import time
import json
import hashlib
from pathlib import Path
from datetime import datetime
import argparse

# mitmproxy imports
from mitmproxy import options, master
from mitmproxy.tools.dump import DumpMaster
from mitmproxy import http, ctx

# Import our content replacer
try:
    from content_replacer import ContentReplacer
except ImportError:
    print("⚠️  ContentReplacer not found. Content replacement will be disabled.")
    ContentReplacer = None


class ContentCaptureAddon:
    """
    Custom mitmproxy addon for capturing web content
    This will be the core of our content capture functionality
    """

    def __init__(self, storage_dir=None, verbose=True, enable_replacement=True):
        self.storage_dir = Path(storage_dir) if storage_dir else Path("./captures")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.verbose = verbose
        self.enable_replacement = enable_replacement
        self.captured_flows = []
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Initialize ContentReplacer if available and enabled
        self.content_replacer = None
        if ContentReplacer and self.enable_replacement:
            try:
                self.content_replacer = ContentReplacer(
                    config_file="replacements.json",
                    data_dir=str(self.storage_dir)
                )
                print(f"✅ Content Replacer initialized with {len(self.content_replacer.list_replacements())} rules")
            except Exception as e:
                print(f"❌ Error initializing ContentReplacer: {e}")
                self.content_replacer = None
        else:
            print("ℹ️  Content replacement disabled")

        print(f"🔧 Content Capture Addon initialized")
        print(f"   Storage directory: {self.storage_dir}")
        print(f"   Session ID: {self.session_id}")
        print(f"   Content replacement: {'✅ Enabled' if self.content_replacer else '❌ Disabled'}")

    def load(self, loader):
        """Called when the addon is loaded"""
        loader.add_option(
            name="capture_enabled",
            typespec=bool,
            default=True,
            help="Enable content capture"
        )
        loader.add_option(
            name="replacement_enabled",
            typespec=bool,
            default=self.enable_replacement,
            help="Enable content replacement"
        )
        print("✅ Content Capture Addon loaded")

    def response(self, flow: http.HTTPFlow):
        """Called when we receive a response from the server"""
        try:
            if not ctx.options.capture_enabled:
                return

            # Extract basic information
            request_url = flow.request.pretty_url
            response_status = flow.response.status_code
            content_type = flow.response.headers.get("content-type", "unknown")

            # Apply content replacement BEFORE capturing
            if self.content_replacer and ctx.options.replacement_enabled and flow.response.content:
                try:
                    original_content = flow.response.content
                    modified_content = self.content_replacer.process_content(
                        original_content,
                        content_type,
                        request_url
                    )

                    # Update the response content if it was modified
                    if modified_content != original_content:
                        flow.response.content = modified_content
                        # Update content length header
                        flow.response.headers["content-length"] = str(len(modified_content))
                        if self.verbose:
                            print(f"🔄 Content modified for: {request_url}")

                except Exception as e:
                    print(f"❌ Error in content replacement for {request_url}: {e}")

            # Generate unique ID for this flow
            flow_id = hashlib.sha256(
                f"{request_url}_{flow.request.timestamp_start}".encode()
            ).hexdigest()[:16]

            # Create capture data
            capture_data = {
                "flow_id": flow_id,
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "request": {
                    "url": request_url,
                    "method": flow.request.method,
                    "headers": dict(flow.request.headers),
                    "host": flow.request.host,
                    "port": flow.request.port,
                    "scheme": flow.request.scheme,
                    "path": flow.request.path
                },
                "response": {
                    "status_code": response_status,
                    "headers": dict(flow.response.headers),
                    "content_type": content_type,
                    "content_length": len(flow.response.content) if flow.response.content else 0,
                    "content_modified": flow.response.content != getattr(flow.response, '_original_content',
                                                                         flow.response.content)
                }
            }

            # Store the content based on type
            self.store_content(flow, capture_data)

            # Add to captured flows list
            self.captured_flows.append(capture_data)

            if self.verbose:
                modification_indicator = "🔄" if capture_data["response"]["content_modified"] else "📡"
                print(
                    f"{modification_indicator} Captured: {flow.request.method} {request_url} → {response_status} ({content_type})")

        except Exception as e:
            print(f"❌ Error in response handler: {e}")

    def store_content(self, flow: http.HTTPFlow, capture_data: dict):
        """Store the actual content based on its type"""
        try:
            flow_id = capture_data["flow_id"]
            content_type = capture_data["response"]["content_type"]

            # Create directory for this flow
            flow_dir = self.storage_dir / flow_id
            flow_dir.mkdir(exist_ok=True)

            # Store metadata
            metadata_file = flow_dir / "metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(capture_data, f, indent=2)

            # Store request content if it exists
            if flow.request.content:
                request_file = flow_dir / "request.bin"
                with open(request_file, 'wb') as f:
                    f.write(flow.request.content)

            # Store response content
            if flow.response.content:
                # Determine file extension based on content type
                if "html" in content_type.lower():
                    response_file = flow_dir / "response.html"
                    content = flow.response.content
                    # Try to decode as text
                    try:
                        content_text = content.decode('utf-8')
                        with open(response_file, 'w', encoding='utf-8') as f:
                            f.write(content_text)
                    except UnicodeDecodeError:
                        # Fall back to binary
                        with open(response_file, 'wb') as f:
                            f.write(content)

                elif "json" in content_type.lower():
                    response_file = flow_dir / "response.json"
                    try:
                        # Pretty print JSON
                        json_data = json.loads(flow.response.content.decode('utf-8'))
                        with open(response_file, 'w') as f:
                            json.dump(json_data, f, indent=2)
                    except:
                        # Fall back to raw content
                        with open(response_file, 'wb') as f:
                            f.write(flow.response.content)

                elif any(t in content_type.lower() for t in ["css", "javascript", "text"]):
                    response_file = flow_dir / "response.txt"
                    try:
                        with open(response_file, 'w', encoding='utf-8') as f:
                            f.write(flow.response.content.decode('utf-8'))
                    except UnicodeDecodeError:
                        with open(response_file, 'wb') as f:
                            f.write(flow.response.content)

                else:
                    # Binary content (images, etc.)
                    response_file = flow_dir / "response.bin"
                    with open(response_file, 'wb') as f:
                        f.write(flow.response.content)

                # Update metadata with file paths
                capture_data["files"] = {
                    "metadata": str(metadata_file),
                    "response": str(response_file)
                }
                if flow.request.content:
                    capture_data["files"]["request"] = str(flow_dir / "request.bin")

                # Update metadata file
                with open(metadata_file, 'w') as f:
                    json.dump(capture_data, f, indent=2)

        except Exception as e:
            print(f"❌ Error storing content for {flow.request.pretty_url}: {e}")

    def get_capture_summary(self):
        """Get a summary of captured content"""
        summary = {
            "session_id": self.session_id,
            "total_flows": len(self.captured_flows),
            "storage_dir": str(self.storage_dir),
            "flows": self.captured_flows[-10:]  # Last 10 flows
        }

        # Add replacement stats if replacer is enabled
        if self.content_replacer:
            summary["replacement_stats"] = self.content_replacer.get_stats()

        return summary

    def reload_replacement_config(self):
        """Reload replacement configuration"""
        if self.content_replacer:
            self.content_replacer.reload_config()
            print("🔄 Replacement configuration reloaded")
        else:
            print("❌ Content replacer not available")

    def get_replacement_stats(self):
        """Get replacement statistics"""
        if self.content_replacer:
            return self.content_replacer.get_stats()
        return {"error": "Content replacer not available"}


class LocalMitmproxy:
    """
    Local mitmproxy server implementation
    """

    def __init__(self, port=8080, host="127.0.0.1", storage_dir=None, verbose=True, enable_replacement=True):
        self.port = port
        self.host = host
        self.storage_dir = storage_dir
        self.verbose = verbose
        self.enable_replacement = enable_replacement
        self.master = None
        self.capture_addon = None
        self.running = False

    def setup_options(self):
        """Set up mitmproxy options"""
        opts = options.Options(
            listen_host=self.host,
            listen_port=self.port,
            http2=True,  # Enable HTTP/2 support
            confdir=str(Path.home() / ".mitmproxy"),  # Certificate directory
            ssl_insecure=False,  # Keep SSL verification on the server side
            # Disable some features that might cause conflicts
            # web_open_browser=False,
            showhost=self.verbose,
        )
        return opts

    def setup_addons(self):
        """Set up mitmproxy addons"""
        addons = []

        # Add our content capture addon
        self.capture_addon = ContentCaptureAddon(
            storage_dir=self.storage_dir,
            verbose=self.verbose,
            enable_replacement=self.enable_replacement
        )
        addons.append(self.capture_addon)

        # Note: Don't add dumper.Dumper() - it's already loaded by default in DumpMaster
        # The verbose output will be handled by the default dumper

        return addons

    async def start(self):
        """Start the mitmproxy server"""
        try:
            print(f"🚀 Starting local mitmproxy server...")
            print(f"   Host: {self.host}")
            print(f"   Port: {self.port}")
            print(f"   Content Replacement: {'✅ Enabled' if self.enable_replacement else '❌ Disabled'}")

            # Set up options and master
            opts = self.setup_options()
            self.master = DumpMaster(opts)

            # Add our addons
            addons = self.setup_addons()
            for addon in addons:
                self.master.addons.add(addon)

            print(f"✅ Mitmproxy configured with {len(addons)} addons")

            # Start the server
            self.running = True
            print(f"🌐 Proxy server listening on {self.host}:{self.port}")
            print(f"📁 Content will be saved to: {self.capture_addon.storage_dir}")

            await self.master.run()

        except Exception as e:
            print(f"❌ Error starting mitmproxy: {e}")
            self.running = False
            raise

    def stop(self):
        """Stop the mitmproxy server"""
        if self.master and self.running:
            print("🛑 Stopping mitmproxy server...")
            self.master.shutdown()
            self.running = False
            print("✅ Mitmproxy server stopped")

    def get_status(self):
        """Get server status"""
        status = {
            "running": self.running,
            "host": self.host,
            "port": self.port,
            "storage_dir": self.storage_dir,
            "replacement_enabled": self.enable_replacement
        }

        if self.capture_addon:
            status["capture_summary"] = self.capture_addon.get_capture_summary()
            if self.capture_addon.content_replacer:
                status["replacement_stats"] = self.capture_addon.get_replacement_stats()

        return status

    def reload_replacement_config(self):
        """Reload replacement configuration"""
        if self.capture_addon:
            self.capture_addon.reload_replacement_config()


def run_mitmproxy_server(port=8080, host="127.0.0.1", storage_dir=None, verbose=True, enable_replacement=True):
    """
    Run the mitmproxy server in the current thread
    """
    proxy = LocalMitmproxy(
        port=port,
        host=host,
        storage_dir=storage_dir,
        verbose=verbose,
        enable_replacement=enable_replacement
    )

    try:
        # Run the async event loop
        asyncio.run(proxy.start())
    except KeyboardInterrupt:
        print("\n⚠️  Received interrupt signal")
        proxy.stop()
    except Exception as e:
        print(f"❌ Server error: {e}")
        proxy.stop()
        raise


def main():
    """Main entry point for running mitmproxy standalone"""
    parser = argparse.ArgumentParser(description="Local mitmproxy server with content capture")
    parser.add_argument("--port", "-p", type=int, default=8080, help="Proxy port (default: 8080)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Proxy host (default: 127.0.0.1)")
    parser.add_argument("--storage", "-s", type=str, help="Storage directory for captures")
    parser.add_argument("--quiet", "-q", action="store_true", help="Quiet mode (less verbose)")
    parser.add_argument("--no-replace", action="store_true", help="Disable content replacement")

    args = parser.parse_args()

    print("🔧 Local Mitmproxy Server")
    print("=" * 50)

    run_mitmproxy_server(
        port=args.port,
        host=args.host,
        storage_dir=args.storage,
        verbose=not args.quiet,
        enable_replacement=not args.no_replace
    )


if __name__ == "__main__":
    main()