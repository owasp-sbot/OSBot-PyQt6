#!/usr/bin/env python3
"""
Content replacement functionality for mitmproxy
Supports regex-based HTML text replacement with JSON configuration
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


class ContentReplacer:
    """
    Handles content replacement based on regex patterns stored in JSON configuration
    """

    def __init__(self, config_file=None, data_dir="./data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        self.config_file = self.data_dir / (config_file or "replacements.json")
        self.replacements = []
        self.stats = {
            "total_processed": 0,
            "total_replaced": 0,
            "last_updated": None
        }

        # Load or create configuration
        self.load_config()

        print(f"🔄 Content Replacer initialized")
        print(f"   Config file: {self.config_file}")
        print(f"   Active replacements: {len(self.replacements)}")

    def load_config(self):
        """Load replacement configuration from JSON file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                self.replacements = config.get("replacements", [])
                self.stats = config.get("stats", self.stats)

                print(f"✅ Loaded {len(self.replacements)} replacement rules")
            else:
                # Create default configuration
                self.create_default_config()

        except Exception as e:
            print(f"❌ Error loading config: {e}")
            self.create_default_config()

    def create_default_config(self):
        """Create a default configuration file with example replacements"""
        default_config = {
            "info": {
                "description": "Content replacement configuration for mitmproxy",
                "created": datetime.now().isoformat(),
                "format": "Each replacement has: pattern (regex), replacement (string), flags (optional), content_types (optional)"
            },
            "replacements": [
                {
                    "name": "Example: Replace 'Google' with 'MODIFIED'",
                    "pattern": r"\bGoogle\b",
                    "replacement": "MODIFIED",
                    "flags": ["IGNORECASE"],
                    "content_types": ["text/html", "application/json"],
                    "enabled": False,
                    "description": "Example replacement - disabled by default"
                },
                {
                    "name": "Example: Add banner to HTML pages",
                    "pattern": r"(<body[^>]*>)",
                    "replacement": r'\1<div style="background: red; color: white; padding: 10px; text-align: center;">⚠️ CONTENT MODIFIED BY PROXY ⚠️</div>',
                    "flags": ["IGNORECASE"],
                    "content_types": ["text/html"],
                    "enabled": False,
                    "description": "Adds a red banner to HTML pages"
                },
                {
                    "name": "Example: Replace specific URLs",
                    "pattern": r"https://example\.com",
                    "replacement": "https://modified-example.com",
                    "content_types": ["text/html", "text/css", "application/javascript"],
                    "enabled": False,
                    "description": "Replace URLs in various content types"
                }
            ],
            "stats": self.stats
        }

        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)

            self.replacements = default_config["replacements"]
            print(f"✅ Created default config: {self.config_file}")

        except Exception as e:
            print(f"❌ Error creating default config: {e}")

    def reload_config(self):
        """Reload configuration from file"""
        print("🔄 Reloading replacement configuration...")
        self.load_config()

    def should_process_content(self, content_type: str, url: str = None) -> bool:
        """Check if content should be processed based on content type"""
        if not content_type:
            return False

        # Common text-based content types that are safe to modify
        processable_types = [
            "text/html",
            "text/plain",
            "text/css",
            "application/javascript",
            "application/json",
            "text/javascript",
            "application/xml",
            "text/xml"
        ]

        return any(ptype in content_type.lower() for ptype in processable_types)

    def process_content(self, content: bytes, content_type: str, url: str = None) -> bytes:
        """
        Process content and apply replacements
        Returns modified content or original content if no changes
        """
        try:
            self.stats["total_processed"] += 1

            if not self.should_process_content(content_type, url):
                return content

            # Get enabled replacements for this content type
            applicable_replacements = self.get_applicable_replacements(content_type)

            if not applicable_replacements:
                return content

            # Decode content to string
            try:
                text_content = content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    text_content = content.decode('latin-1')
                except UnicodeDecodeError:
                    # Can't decode, return original
                    return content

            original_content = text_content
            modified = False

            # Apply each replacement
            for replacement in applicable_replacements:
                try:
                    pattern = replacement["pattern"]
                    replace_with = replacement["replacement"]
                    flags = self.parse_regex_flags(replacement.get("flags", []))

                    # Compile regex with flags
                    regex = re.compile(pattern, flags)

                    # Apply replacement
                    new_content = regex.sub(replace_with, text_content)

                    if new_content != text_content:
                        print(f"🔄 Applied replacement '{replacement['name']}' to {url}")
                        text_content = new_content
                        modified = True

                except Exception as e:
                    print(f"❌ Error applying replacement '{replacement.get('name', 'unknown')}': {e}")

            if modified:
                self.stats["total_replaced"] += 1
                self.stats["last_updated"] = datetime.now().isoformat()

                # Encode back to bytes
                return text_content.encode('utf-8')

            return content

        except Exception as e:
            print(f"❌ Error processing content: {e}")
            return content

    def get_applicable_replacements(self, content_type: str) -> List[Dict]:
        """Get replacements that apply to the given content type"""
        applicable = []

        for replacement in self.replacements:
            # Skip disabled replacements
            if not replacement.get("enabled", True):
                continue

            # Check content type filter
            allowed_types = replacement.get("content_types", [])
            if allowed_types:
                if not any(ctype in content_type.lower() for ctype in allowed_types):
                    continue

            applicable.append(replacement)

        return applicable

    def parse_regex_flags(self, flag_names: List[str]) -> int:
        """Convert flag names to regex flags"""
        flags = 0
        flag_map = {
            "IGNORECASE": re.IGNORECASE,
            "MULTILINE": re.MULTILINE,
            "DOTALL": re.DOTALL,
            "VERBOSE": re.VERBOSE,
            "ASCII": re.ASCII,
            "LOCALE": re.LOCALE
        }

        for flag_name in flag_names:
            if flag_name.upper() in flag_map:
                flags |= flag_map[flag_name.upper()]

        return flags

    def add_replacement(self, name: str, pattern: str, replacement: str,
                        content_types: List[str] = None, flags: List[str] = None,
                        enabled: bool = True, description: str = ""):
        """Add a new replacement rule"""
        new_replacement = {
            "name": name,
            "pattern": pattern,
            "replacement": replacement,
            "content_types": content_types or ["text/html"],
            "flags": flags or [],
            "enabled": enabled,
            "description": description,
            "created": datetime.now().isoformat()
        }

        self.replacements.append(new_replacement)
        self.save_config()
        print(f"✅ Added replacement rule: {name}")

    def save_config(self):
        """Save current configuration to file"""
        try:
            config = {
                "info": {
                    "description": "Content replacement configuration for mitmproxy",
                    "last_updated": datetime.now().isoformat()
                },
                "replacements": self.replacements,
                "stats": self.stats
            }

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            print(f"✅ Configuration saved to {self.config_file}")

        except Exception as e:
            print(f"❌ Error saving config: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get replacement statistics"""
        return {
            **self.stats,
            "active_replacements": len([r for r in self.replacements if r.get("enabled", True)]),
            "total_replacements": len(self.replacements)
        }

    def list_replacements(self) -> List[Dict]:
        """Get list of all replacement rules"""
        return self.replacements

    def enable_replacement(self, name: str, enabled: bool = True):
        """Enable or disable a replacement by name"""
        for replacement in self.replacements:
            if replacement["name"] == name:
                replacement["enabled"] = enabled
                self.save_config()
                print(f"✅ {'Enabled' if enabled else 'Disabled'} replacement: {name}")
                return True

        print(f"❌ Replacement not found: {name}")
        return False


# Example usage and testing
if __name__ == "__main__":
    # Test the content replacer
    replacer = ContentReplacer(data_dir="./test_data")

    # Test HTML content
    html_content = b"""
    <html>
    <head><title>Google Search</title></head>
    <body>
        <h1>Welcome to Google</h1>
        <p>This is a test page from Google.</p>
        <a href="https://example.com">Example Link</a>
    </body>
    </html>
    """

    print("\n🧪 Testing content replacement...")
    print("Original content length:", len(html_content))

    # Process the content
    modified_content = replacer.process_content(
        html_content,
        "text/html",
        "https://www.google.com/"
    )

    print("Modified content length:", len(modified_content))
    print("Content changed:", modified_content != html_content)

    # Show stats
    print("\n📊 Replacement Stats:")
    stats = replacer.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # Show replacements
    print(f"\n📋 Replacement Rules ({len(replacer.list_replacements())}):")
    for i, replacement in enumerate(replacer.list_replacements(), 1):
        status = "✅" if replacement.get("enabled", True) else "❌"
        print(f"   {i}. {status} {replacement['name']}")
        print(f"      Pattern: {replacement['pattern']}")
        print(f"      Types: {replacement.get('content_types', ['any'])}")