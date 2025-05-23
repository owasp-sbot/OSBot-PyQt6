# Web Content Capture - PyQt6 Edition

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.0+-green.svg)](https://pypi.org/project/PyQt6/)
[![mitmproxy](https://img.shields.io/badge/mitmproxy-Latest-orange.svg)](https://mitmproxy.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A **self-contained, desktop application** for capturing and analyzing web content with real-time content replacement capabilities. Built with PyQt6 + mitmproxy for comprehensive web traffic interception and modification.

## 🎯 **What This Does**

- **🌐 Full Web Browser**: Chromium-based browser with complete SSL bypass
- **📡 Traffic Capture**: Intercepts and saves ALL HTTP/HTTPS requests/responses  
- **🔄 Content Replacement**: Real-time regex-based content modification via JSON config
- **📁 Organized Storage**: Automatic content organization with metadata
- **🔒 Self-Contained**: No system modifications, admin privileges, or external dependencies

## 🚀 **Quick Start**

### Prerequisites
```bash
pip install PyQt6 PyQt6-WebEngine mitmproxy fastapi uvicorn requests
```

### Run the Application
```bash
python integrated_main_app.py --proxy-port 8080
```

### Test Content Replacement
1. Edit `./data/replacements.json` 
2. Enable a replacement rule: `"enabled": true`
3. Browse websites and see content modified in real-time!

## 📊 **Current Features**

### ✅ **Core Functionality**
- **Integrated mitmproxy server** running locally in Python
- **SSL certificate bypass** with aggressive QtWebEngine configuration
- **Automatic content capture** for all web traffic (HTML, JSON, CSS, JS, images)
- **Real-time content replacement** using regex patterns
- **Dual-mode operation**: Browser + Capture Log tabs
- **FastAPI backend** for content management and storage

### ✅ **Content Replacement System**
- **JSON configuration** stored in `./data/replacements.json`
- **Regex pattern matching** with flags (IGNORECASE, MULTILINE, etc.)
- **Content-type filtering** (HTML, JSON, CSS, JavaScript)
- **Live reload** capability for testing replacements
- **Replacement statistics** and tracking

### ✅ **Browser Integration**
- **PyQt6 WebEngine** with Chromium rendering
- **Proxy auto-configuration** routing all traffic through mitmproxy
- **SSL bypass** without system certificate store modifications
- **Navigation controls** (back, forward, reload, URL bar)
- **Status indicators** for proxy, SSL, and capture states

## 🏗️ **Architecture Overview**

```
┌─────────────────────────────────────┐
│        PyQt6 Desktop App            │
│  ┌─────────────────────────────────┐│
│  │     QtWebEngine Browser         ││  
│  │   (SSL Bypass + Proxy Config)   ││
│  └─────────────────────────────────┘│
└─────────────────┬───────────────────┘
                  │ All HTTP/HTTPS Traffic
                  ▼
┌─────────────────────────────────────┐
│       Local mitmproxy Server        │
│  ┌─────────────────────────────────┐│
│  │    ContentCaptureAddon          ││
│  │  • Intercepts all requests      ││  
│  │  • Applies content replacements ││
│  │  • Saves organized content      ││
│  └─────────────────────────────────┘│
└─────────────────┬───────────────────┘
                  │ Processed Content
                  ▼
┌─────────────────────────────────────┐
│         Content Storage             │
│  • ./captures/ (organized by flow) │
│  • ./data/replacements.json        │
│  • FastAPI backend integration     │
└─────────────────────────────────────┘
```

## 📂 **Project Structure**

```
OSBot-PyQt6/
│
├── owasp_pyqt6/
│   ├── integrated_main_app.py      # Main application with integrated UI
│   ├── start_mitmproxy.py          # Standalone mitmproxy server  
│   ├── content_replacer.py         # Content replacement engine
│   ├── server.py                   # FastAPI backend
│   └── build_macos.py              # macOS build script
│
├── data/
│   └── replacements.json           # Content replacement configuration
│
├── captures/                       # Captured web content (auto-created)
│   ├── [flow-id]/
│   │   ├── metadata.json
│   │   ├── response.html
│   │   └── request.bin
│   └── ...
│
└── docs/                          # Documentation
    ├── architecture.md
    ├── content-replacement.md
    ├── ssl-bypass.md
    └── development.md
```

## 🎮 **Usage Examples**

### Basic Web Browsing
```bash
# Start the application
python integrated_main_app.py

# Navigate to any website
# All traffic automatically captured to ./captures/
```

### Content Replacement
```json
// Edit ./data/replacements.json
{
  "replacements": [
    {
      "name": "Replace Google with MODIFIED",
      "pattern": "\\bGoogle\\b",
      "replacement": "MODIFIED",
      "flags": ["IGNORECASE"],
      "content_types": ["text/html"],
      "enabled": true
    }
  ]
}
```

### Standalone mitmproxy
```bash
# Run just the proxy server
python start_mitmproxy.py --port 8080

# With custom storage location
python start_mitmproxy.py --port 8080 --storage ./my_captures
```

## 🔧 **Configuration**

### SSL Bypass Configuration
The application uses multiple layers of SSL bypass:
- **Environment variables** for QtWebEngine flags
- **Command-line arguments** (`--ignore-certificate-errors`, `--test-type`)
- **Custom certificate handling** for mitmproxy CA certificate

### Content Replacement Rules
Each replacement rule supports:
- **Pattern**: Regex pattern to match
- **Replacement**: String replacement (supports backreferences)
- **Flags**: Regex flags (IGNORECASE, MULTILINE, DOTALL, etc.)
- **Content Types**: Filter by MIME type
- **Enable/Disable**: Individual rule control

## 📈 **What's Working (MVP Status)**

### ✅ **Fully Functional**
- **Desktop application** with integrated browser
- **Local mitmproxy server** with Python integration
- **SSL certificate bypass** without system modifications  
- **Content capture** for all web traffic types
- **Real-time content replacement** with JSON configuration
- **Organized content storage** with metadata
- **Cross-platform compatibility** (macOS, Windows, Linux)

### ✅ **Tested & Verified**
- **HTTPS sites load** without certificate errors
- **Content replacement works** in real-time 
- **All traffic captured** and properly organized
- **Regex patterns** with various flags function correctly
- **Multiple content types** supported (HTML, JSON, CSS, JS)

## 🚧 **Next Steps & Roadmap**

### 📋 **Immediate Improvements**
- [ ] **Enhanced UI** for replacement rule management
- [ ] **Content search/filter** capabilities in captured data
- [ ] **Export functionality** for captured content
- [ ] **Rule templates** for common replacement patterns
- [ ] **Performance optimization** for large-scale captures

### 🎯 **Advanced Features** 
- [ ] **Content analysis** with ML/NLP integration
- [ ] **Automated content verification** and fact-checking
- [ ] **Multi-user collaboration** features
- [ ] **API integration** for external analysis tools
- [ ] **Scheduled capture** capabilities
- [ ] **Advanced filtering** and search capabilities

### 🏗️ **Technical Enhancements**
- [ ] **Plugin architecture** for extensible functionality
- [ ] **Database integration** for large-scale content storage
- [ ] **Distributed capture** across multiple instances
- [ ] **Real-time streaming** API for captured content
- [ ] **Advanced SSL handling** for complex scenarios

## 🎥 **Demo & Resources**

- **📺 Demo Video**: [YouTube - Web Content Capture MVP](https://www.youtube.com/watch?v=s7G42SIdAX8)
- **💼 LinkedIn Post**: [Project Announcement](https://www.linkedin.com/feed/update/urn:li:activity:7331359941871476737/)
- **📁 GitHub Repository**: [OSBot-PyQt6](https://github.com/owasp-sbot/OSBot-PyQt6/tree/dev)

## 🤝 **Contributing**

We welcome contributions! Here's how to get started:

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Commit** your changes: `git commit -m 'Add amazing feature'`
4. **Push** to the branch: `git push origin feature/amazing-feature`
5. **Submit** a Pull Request

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 **Acknowledgments**

- **mitmproxy** team for the excellent proxy framework
- **PyQt6** for robust desktop application capabilities  
- **FastAPI** for the clean API framework
- **OWASP** community for security-focused development practices

---

*For detailed documentation, see the [/docs](./docs/) folder*