# OSBot-PyQt6 - Web Content Capture

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.0+-green.svg)](https://pypi.org/project/PyQt6/)
[![mitmproxy](https://img.shields.io/badge/mitmproxy-Integrated-orange.svg)](https://mitmproxy.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A powerful desktop application for capturing, analyzing, and modifying web content in real-time. Built with PyQt6 and an integrated mitmproxy server for comprehensive web traffic interception and modification.

## 🎯 **Key Features**

- **🌐 Full Web Browser**: Chromium-based browser with complete SSL/TLS interception
- **📡 Traffic Capture**: Intercepts and saves all HTTP/HTTPS requests and responses  
- **🔄 Real-time Content Replacement**: Modify web content on-the-fly using regex patterns
- **📁 Organized Storage**: Automatic content organization with detailed metadata
- **🔒 Self-Contained**: No system modifications or admin privileges required
- **🎨 Intuitive UI**: Tabbed interface for browsing, capture logs, and rule management

## 🚀 **Quick Start**

### Prerequisites
```bash
pip install PyQt6 PyQt6-WebEngine mitmproxy fastapi uvicorn requests osbot-utils
```

### Run the Application
```bash
cd osbot_pyqt6
python3 ./main_app.py
```

The application will start with:
- Integrated mitmproxy on port 8080
- FastAPI backend on port 8000
- Browser with automatic proxy configuration

## 📸 **Screenshots**

### Main Browser Interface
![Main Browser with Content Replacement](https://github.com/user-attachments/assets/754a5475-b015-4d25-a09f-ef4ff03e31a3)
*Web browser showing real-time content modification - notice how "Dinis" is replaced with "MODIFIED" throughout the page*

### Content Interception in Action
![BBC Sports Interception](https://github.com/user-attachments/assets/04b73714-7e13-4330-b71e-17ba0320759d)
*BBC Sports page with injected warning banner demonstrating content modification capabilities*

### Rule Management Interface
![Content Replacement Rules](https://github.com/user-attachments/assets/22537999-b29b-4ca7-b9f3-f853ed3963e4)
*Configuration interface showing active replacement rules and statistics*

## 📊 **Core Functionality**

### ✅ **Integrated Components**
- **Local mitmproxy server** running within the Python application
- **SSL/TLS interception** with automatic certificate handling
- **Content capture** for all web traffic (HTML, JSON, CSS, JS, images, etc.)
- **Real-time content replacement** using configurable regex patterns
- **Three-tab interface**: Browser, Capture Log, and Content Replacement
- **FastAPI backend** for content management and API access

### ✅ **Content Replacement System**
- **JSON-based configuration** stored in `./captures/replacements.json`
- **Regex pattern matching** with full flag support (IGNORECASE, MULTILINE, etc.)
- **Content-type filtering** (HTML, JSON, CSS, JavaScript)
- **Live reload** - changes take effect immediately
- **Visual indicators** showing which content has been modified
- **Replacement statistics** tracking

### ✅ **Capture Capabilities**
- **Automatic content organization** by flow ID
- **Complete metadata storage** (headers, timestamps, status codes)
- **Content-aware file storage** (HTML as .html, JSON as .json, etc.)
- **Performance optimized** loading with duration tracking
- **Visual indicators** (🔄 for modified content, 📡 for original)

## 🏗️ **Architecture Overview**

```
┌─────────────────────────────────────┐
│        PyQt6 Desktop App            │
│  ┌─────────────────────────────────┐│
│  │     QtWebEngine Browser         ││  
│  │   (SSL Bypass + Auto Proxy)     ││
│  └─────────────────────────────────┘│
│  ┌─────────────────────────────────┐│
│  │    Tab Interface                ││
│  │  • Browser                      ││
│  │  • Capture Log                  ││
│  │  • Content Replacement          ││
│  └─────────────────────────────────┘│
└─────────────────┬───────────────────┘
                  │ All Traffic
                  ▼
┌─────────────────────────────────────┐
│    Integrated mitmproxy Server      │
│  ┌─────────────────────────────────┐│
│  │    ContentCaptureAddon          ││
│  │  • Intercepts requests/responses││  
│  │  • Applies replacements         ││
│  │  • Saves content & metadata     ││
│  └─────────────────────────────────┘│
│  ┌─────────────────────────────────┐│
│  │    ContentReplacer              ││
│  │  • Regex pattern matching       ││
│  │  • Content-type filtering       ││
│  │  • Real-time modification       ││
│  └─────────────────────────────────┘│
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│         Storage Layer               │
│  • ./captures/[flow-id]/            │
│    - metadata.json                  │
│    - response.html/json/txt         │
│    - request.bin                    │
│  • ./captures/replacements.json     │
└─────────────────────────────────────┘
```

## 📂 **Project Structure**

```
OSBot-PyQt6/
├── osbot_pyqt6/
│   ├── main_app.py                 # Main application entry point
│   ├── start_mitmproxy.py          # Integrated mitmproxy implementation
│   ├── content_replacer.py         # Content replacement engine
│   ├── server.py                   # FastAPI backend server
│   ├── Version.py                  # Version management
│   └── __init__.py                 # Package initialization
│
├── captures/                       # Auto-created storage directory
│   ├── replacements.json           # Content replacement rules
│   └── [flow-id]/                  # Captured content by flow
│       ├── metadata.json
│       ├── response.html
│       └── request.bin
│
└── README.md                       # This file
```

## 🎮 **Usage Examples**

### Basic Web Browsing with Capture
```bash
# Start the application
cd osbot_pyqt6
python3 ./main_app.py

# All web traffic is automatically captured
# Check the Capture Log tab to see intercepted requests
```

### Content Replacement Configuration
```json
{
  "replacements": [
    {
      "name": "Replace 'Dinis' with 'MODIFIED'",
      "pattern": "\\bDinis\\b",
      "replacement": "******MODIFIED****",
      "flags": ["IGNORECASE"],
      "content_types": ["text/html", "application/json"],
      "enabled": true,
      "description": "Example replacement"
    },
    {
      "name": "Add banner to HTML pages",
      "pattern": "(<body[^>]*>)",
      "replacement": "\\1<div style=\"background: black; color: white; padding: 10px; text-align: center;\">⚠️ CONTENT MODIFIED BY PROXY ⚠️</div>",
      "flags": ["IGNORECASE"],
      "content_types": ["text/html"],
      "enabled": true
    }
  ]
}
```

### Command Line Options
```bash
# Custom ports
python3 ./main_app.py --api-port 8001 --proxy-port 8081

# Disable content replacement
python3 ./main_app.py --no-replacement

# Quiet mode (less verbose output)
python3 ./main_app.py --quiet
```

## 🔧 **Configuration**

### Environment Variables
The application automatically sets up required environment variables for SSL bypass:
- `QTWEBENGINE_CHROMIUM_FLAGS`: Comprehensive SSL and security bypass flags
- `QTWEBENGINE_DISABLE_SANDBOX`: Disabled for development
- `QTWEBENGINE_REMOTE_DEBUGGING`: Port 9222 for debugging

### Content Replacement Rules
Each rule in `replacements.json` supports:
- **name**: Descriptive name for the rule
- **pattern**: Regular expression pattern
- **replacement**: Replacement string (supports backreferences)
- **flags**: Array of regex flags (IGNORECASE, MULTILINE, DOTALL, etc.)
- **content_types**: Array of MIME types to apply the rule to
- **enabled**: Boolean to enable/disable the rule
- **description**: Optional description

## 📈 **Features in Action**

### Real-time Content Modification
- Modify any text content as it passes through the proxy
- See changes instantly in the browser
- Visual indicators show modified content (🔄) vs original (📡)

### Comprehensive Capture
- Every request and response is captured
- Organized storage with metadata
- Quick access to captured content through the Capture Log tab

### Easy Rule Management
- Edit rules through the UI or directly in JSON
- Reload rules without restarting the application
- View statistics on rule applications

## 🚧 **Troubleshooting**

### Common Issues

**Browser doesn't load HTTPS sites:**
- Ensure mitmproxy is running (check Proxy status indicator)
- SSL bypass is automatically configured

**Content replacement not working:**
- Check that replacement is enabled (green status indicator)
- Verify your regex patterns in the Content Replacement tab
- Ensure the content type matches your rule configuration

**Application won't start:**
- Install all dependencies: `pip install PyQt6 PyQt6-WebEngine mitmproxy fastapi uvicorn requests osbot-utils`
- Check that ports 8080 (proxy) and 8000 (API) are available

## 🤝 **Contributing**

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 **Acknowledgments**

- **mitmproxy** team for the excellent proxy framework
- **PyQt6** for robust desktop application capabilities  
- **FastAPI** for the clean API framework
- **OWASP** community for security research and tools

---

**Note**: This tool is intended for authorized security testing, web development, and research purposes only. Always ensure you have permission before intercepting or modifying web traffic.