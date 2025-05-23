# Documentation

Welcome to the **Web Content Capture** documentation! This directory contains comprehensive technical documentation covering all aspects of the application's architecture, implementation, and usage.

## 📖 **Documentation Overview**

| Document | Description | Audience |
|----------|-------------|----------|
| [architecture.md](architecture.md) | Technical architecture and design decisions | Developers, Architects |
| [content-replacement.md](content-replacement.md) | Content replacement system guide | Users, Developers |
| [ssl-bypass.md](ssl-bypass.md) | SSL bypass implementation details | Developers, Security Researchers |
| [development.md](development.md) | Development setup and contribution guide | Contributors, Maintainers |

## 🚀 **Quick Navigation**

### **For Users**
- 🔄 **[Content Replacement Guide](content-replacement.md)** - Learn how to configure and use the regex-based content replacement system
- 📝 **[Usage Examples](content-replacement.md#advanced-examples)** - Real-world examples of content modification patterns

### **For Developers**
- 🏗️ **[Architecture Overview](architecture.md#component-architecture)** - Understand the system's technical architecture
- 💻 **[Development Setup](development.md#development-environment-setup)** - Get started with local development
- 🧪 **[Testing Guide](development.md#testing-framework)** - Learn about the testing framework and procedures

### **For Security Researchers**
- 🔒 **[SSL Bypass Implementation](ssl-bypass.md)** - Deep dive into the three-layer SSL bypass system
- 🛡️ **[Security Considerations](ssl-bypass.md#security-implications)** - Understanding security implications and best practices

### **For System Administrators**
- 📦 **[Build and Distribution](development.md#build-and-distribution)** - Creating deployable packages
- ⚙️ **[Configuration Management](content-replacement.md#configuration)** - Managing application configuration

## 🎯 **Documentation Highlights**

### **What Makes This Project Unique**

#### **Python-Native Architecture**
- **Unified Technology Stack**: 100% Python implementation
- **Self-Contained**: No system modifications or admin privileges required
- **Cross-Platform**: Works on macOS, Windows, and Linux

#### **Advanced SSL Bypass**
- **Three-Layer Approach**: Environment variables + command-line args + certificate management
- **No System Changes**: Bypasses SSL without modifying system certificate stores
- **Seamless UX**: HTTPS sites load without certificate warnings

#### **Real-Time Content Replacement**
- **Regex-Based**: Powerful pattern matching and replacement
- **JSON Configuration**: Easy-to-manage replacement rules
- **Content-Type Aware**: Selective processing based on MIME types

## 📋 **Document Summaries**

### **[architecture.md](architecture.md)** - Technical Architecture
```
🏗️ System Architecture and Design
├── Architectural Evolution (Electron → Python)
├── Component Architecture (PyQt6 + mitmproxy + FastAPI)
├── SSL Bypass Architecture (Three-layer approach)
├── Data Flow Diagrams (Request/response processing)
├── Threading Model (Multi-threaded architecture)
└── Performance Characteristics (Resource usage and optimization)
```

**Key Sections:**
- Component interaction diagrams
- SSL bypass technical details
- Data flow and processing pipelines
- Threading and concurrency patterns

### **[content-replacement.md](content-replacement.md)** - Content Replacement System
```
🔄 Content Replacement Guide
├── JSON Configuration Format
├── Regex Pattern Examples
├── Content-Type Filtering
├── Advanced Use Cases
├── Testing and Debugging
└── Best Practices
```

**Key Sections:**
- Complete configuration reference
- Real-world pattern examples
- Troubleshooting common issues
- Performance optimization tips

### **[ssl-bypass.md](ssl-bypass.md)** - SSL Bypass Implementation
```
🔒 SSL Bypass Technical Guide
├── Three-Layer Bypass Strategy
├── Implementation Details
├── Platform-Specific Considerations
├── Troubleshooting Guide
├── Security Implications
└── Advanced Configuration
```

**Key Sections:**
- Critical `--test-type` flag explanation
- Environment variable timing
- Certificate management strategies
- Security best practices

### **[development.md](development.md)** - Development Guide
```
💻 Development and Contribution Guide
├── Environment Setup
├── Code Organization
├── Development Workflow
├── Testing Framework
├── Build and Distribution
└── Contributing Guidelines
```

**Key Sections:**
- Complete development environment setup
- Code style and standards
- Testing procedures and frameworks
- Release and deployment processes

## 🔧 **Getting Started Paths**

### **Path 1: User/Tester**
1. Start with **[Main README](../README.md)** for quick start
2. Read **[Content Replacement Guide](content-replacement.md)** for usage
3. Check **[SSL Bypass Guide](ssl-bypass.md#verification-and-testing)** for troubleshooting

### **Path 2: Developer/Contributor**
1. Review **[Architecture Overview](architecture.md)** for system understanding
2. Follow **[Development Setup](development.md#development-environment-setup)** 
3. Read **[Contributing Guidelines](development.md#contributing-guidelines)**

### **Path 3: Security Researcher**
1. Study **[SSL Bypass Implementation](ssl-bypass.md)** for technical details
2. Review **[Security Considerations](ssl-bypass.md#security-implications)**
3. Check **[Architecture Security](architecture.md#security-architecture)**

### **Path 4: System Administrator**
1. Review **[Build and Distribution](development.md#build-and-distribution)**
2. Study **[Configuration Management](content-replacement.md#configuration)**
3. Check **[Performance Optimization](development.md#performance-optimization)**

## 📚 **Additional Resources**

### **External Documentation**
- **[PyQt6 Documentation](https://doc.qt.io/qtforpython/)** - PyQt6 framework reference
- **[mitmproxy Documentation](https://docs.mitmproxy.org/)** - mitmproxy proxy toolkit
- **[FastAPI Documentation](https://fastapi.tiangolo.com/)** - FastAPI web framework

### **Project Resources**
- **[Demo Video](https://www.youtube.com/watch?v=s7G42SIdAX8)** - Complete walkthrough of the MVP
- **[LinkedIn Post](https://www.linkedin.com/feed/update/urn:li:activity:7331359941871476737/)** - Project announcement
- **[GitHub Repository](https://github.com/owasp-sbot/OSBot-PyQt6)** - Source code and issues

## 🤝 **Documentation Contributions**

We welcome contributions to improve the documentation! Here's how to help:

### **How to Contribute**
1. **Fork** the repository
2. **Edit** documentation files in the `/docs` folder
3. **Follow** the existing style and format
4. **Submit** a pull request with your improvements

### **Documentation Standards**
- **Clear Structure**: Use consistent headers and organization
- **Code Examples**: Provide working code snippets
- **Visual Aids**: Include diagrams and flowcharts where helpful
- **Cross-References**: Link between related sections
- **Keep Updated**: Ensure documentation matches current implementation

### **What Needs Documentation**
- [ ] **API Reference**: Complete FastAPI endpoint documentation
- [ ] **Configuration Reference**: All configuration options and defaults
- [ ] **Troubleshooting Guide**: Common issues and solutions
- [ ] **Performance Tuning**: Optimization guides for different scenarios
- [ ] **Deployment Guides**: Platform-specific deployment instructions

## 🔍 **Quick Reference**

### **Common Configuration Files**
- `data/replacements.json` - Content replacement rules
- `captures/` - Captured web content (auto-created)
- `~/.mitmproxy/` - mitmproxy certificates and configuration

### **Key Command Line Options**
```bash
# Basic usage
python integrated_main_app.py --proxy-port 8080

# Development mode
python start_mitmproxy.py --port 8080 --storage ./test_captures

# Build application
python build_macos.py --sign --cert-name "Developer ID"
```

### **Important Environment Variables**
```bash
QTWEBENGINE_CHROMIUM_FLAGS    # SSL bypass configuration
QTWEBENGINE_DISABLE_SANDBOX   # Sandbox control
```

### **Essential Debugging Commands**
```bash
# Check SSL bypass status
python -c "import os; print(os.environ.get('QTWEBENGINE_CHROMIUM_FLAGS'))"

# Test mitmproxy certificate
curl http://localhost:8080/cert/pem

# View captured content
ls -la captures/
```

---

**📄 Need Help?** 
- Check the relevant documentation section above
- Review the [main README](../README.md) for quick start guide
- Submit an issue on [GitHub](https://github.com/owasp-sbot/OSBot-PyQt6/issues) for specific problems

**💡 Have Suggestions?**
- Open a discussion on [GitHub](https://github.com/owasp-sbot/OSBot-PyQt6/discussions)
- Submit a pull request with improvements
- Contact the maintainers via [LinkedIn](https://www.linkedin.com/feed/update/urn:li:activity:7331359941871476737/)

*This documentation reflects the current state of the MVP and will be updated as the project evolves.*