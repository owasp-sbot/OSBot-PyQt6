# Development Guide

## Getting Started

This guide covers development setup, code organization, testing procedures, and contribution guidelines for the Web Content Capture project.

## Development Environment Setup

### Prerequisites

#### Python Environment
```bash
# Python 3.12+ required
python --version

# Create virtual environment
python -m venv venv

# Activate virtual environment
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

#### Core Dependencies
```bash
# Install core packages
pip install PyQt6 PyQt6-WebEngine mitmproxy fastapi uvicorn requests

# Development dependencies
pip install pytest pytest-qt black flake8 mypy

# Optional: Documentation
pip install mkdocs mkdocs-material
```

#### System Requirements

**macOS:**
```bash
# Xcode Command Line Tools (for PyQt6 compilation)
xcode-select --install

# Optional: Homebrew for additional tools
brew install git python3
```

**Linux (Ubuntu/Debian):**
```bash
# System dependencies for PyQt6
sudo apt update
sudo apt install python3-dev python3-pip build-essential
sudo apt install qt6-base-dev qt6-webengine-dev

# X11 dependencies (if running headless)
sudo apt install xvfb
```

**Windows:**
```bash
# Visual Studio Build Tools (for some dependencies)
# Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/

# Git for Windows
# Download from: https://git-scm.com/download/win
```

### Project Setup

#### Clone Repository
```bash
git clone https://github.com/owasp-sbot/OSBot-PyQt6.git
cd OSBot-PyQt6
git checkout dev  # Development branch
```

#### Install in Development Mode
```bash
# Install package in editable mode
pip install -e .

# Install development dependencies
pip install -r requirements-dev.txt
```

## Code Organization

### Project Structure
```
OSBot-PyQt6/
├── osbot_pyqt6/                 # Main package
│   ├── __init__.py
│   ├── integrated_main_app.py   # Main application entry point
│   ├── start_mitmproxy.py       # Standalone mitmproxy server
│   ├── content_replacer.py      # Content replacement engine
│   ├── server.py                # FastAPI backend
│   └── build_macos.py           # Build scripts
│
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── test_content_replacer.py
│   ├── test_ssl_bypass.py
│   └── test_integration.py
│
├── docs/                        # Documentation
│   ├── architecture.md
│   ├── content-replacement.md
│   ├── ssl-bypass.md
│   └── development.md
│
├── data/                        # Configuration files
│   └── replacements.json
│
├── captures/                    # Captured content (auto-created)
├── requirements.txt             # Production dependencies
├── requirements-dev.txt         # Development dependencies
├── setup.py                     # Package setup
└── README.md                    # Project overview
```

### Key Components

#### 1. Main Application (`integrated_main_app.py`)
```python
# Entry point for the desktop application
# Integrates: PyQt6 UI + mitmproxy + FastAPI + SSL bypass

class WebCaptureBrowser(QMainWindow):
    """Main application window with integrated components"""
    
    def __init__(self):
        # Initialize UI components
        # Start background services (mitmproxy, FastAPI)
        # Configure SSL bypass
        # Set up content capture
```

#### 2. Content Replacement (`content_replacer.py`)
```python
# Regex-based content modification system
# JSON configuration management
# Content type filtering and processing

class ContentReplacer:
    """Handles regex-based content replacement"""
    
    def process_content(self, content, content_type, url):
        # Apply replacement rules to content
        # Track statistics and modifications
        # Return modified content
```

#### 3. mitmproxy Integration (`start_mitmproxy.py`)
```python
# Local mitmproxy server with custom addons
# Traffic interception and content capture
# Integration with content replacement system

class ContentCaptureAddon:
    """mitmproxy addon for content capture and replacement"""
    
    def response(self, flow):
        # Intercept HTTP/HTTPS responses
        # Apply content replacements
        # Store captured content with metadata
```

## Development Workflow

### 1. Feature Development

#### Branch Strategy
```bash
# Create feature branch from dev
git checkout dev
git pull origin dev
git checkout -b feature/your-feature-name

# Make changes...
git add .
git commit -m "feat: add new feature description"

# Push and create PR
git push origin feature/your-feature-name
```

#### Code Style
```bash
# Format code with Black
black osbot_pyqt6/

# Lint with flake8
flake8 osbot_pyqt6/

# Type checking with mypy
mypy osbot_pyqt6/
```

### 2. Testing

#### Unit Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_content_replacer.py

# Run with coverage
pytest --cov=osbot_pyqt6

# Run GUI tests (requires X11/display)
pytest tests/test_gui.py
```

#### Integration Tests
```bash
# Test SSL bypass functionality
python tests/test_ssl_bypass.py

# Test mitmproxy integration
python tests/test_mitmproxy_integration.py

# End-to-end testing
python tests/test_e2e.py
```

#### Manual Testing
```bash
# Start development server
python osbot_pyqt6/integrated_main_app.py --proxy-port 8080

# Test content replacement
# 1. Edit data/replacements.json
# 2. Enable a test rule
# 3. Navigate to target website
# 4. Verify content modification
# 5. Check capture logs
```

### 3. Debugging

#### Application Debugging
```python
# Enable debug mode
import logging
logging.basicConfig(level=logging.DEBUG)

# Add debug prints
print(f"🐛 Debug: {variable_name}")

# Use Qt debugger
from PyQt6.QtCore import QLoggingCategory
QLoggingCategory.setFilterRules("qt.network.ssl.debug=true")
```

#### mitmproxy Debugging
```bash
# Start mitmproxy with verbose logging
python start_mitmproxy.py --port 8080 -v

# Check mitmproxy logs
tail -f ~/.mitmproxy/mitmproxy.log

# Interactive mitmproxy debugging
mitmdump -p 8080 -s debug_addon.py
```

#### SSL Bypass Debugging
```python
# Check environment variables
import os
print("SSL Flags:", os.environ.get('QTWEBENGINE_CHROMIUM_FLAGS'))

# Verify command line arguments
print("sys.argv:", sys.argv)

# Test certificate download
curl http://localhost:8080/cert/pem
```

## Testing Framework

### Test Structure

#### Unit Tests
```python
# tests/test_content_replacer.py
import pytest
from osbot_pyqt6.content_replacer import ContentReplacer

class TestContentReplacer:
    def setup_method(self):
        self.replacer = ContentReplacer(data_dir="./test_data")
    
    def test_basic_replacement(self):
        content = b"Hello Google World"
        # Enable test replacement rule
        result = self.replacer.process_content(content, "text/html", "test.com")
        assert b"MODIFIED" in result
```

#### GUI Tests
```python
# tests/test_gui.py  
import pytest
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt
from osbot_pyqt6.integrated_main_app import WebCaptureBrowser

@pytest.fixture
def app(qtbot):
    browser = WebCaptureBrowser()
    qtbot.addWidget(browser)
    return browser

def test_navigation(app, qtbot):
    # Test URL navigation
    app.url_edit.setText("https://httpbin.org")
    QTest.keyClick(app.url_edit, Qt.Key.Key_Return)
    
    # Wait for page load
    qtbot.waitUntil(lambda: app.web_view.url().toString().startswith("https://httpbin.org"))
```

#### Integration Tests
```python
# tests/test_integration.py
import asyncio
import pytest
from osbot_pyqt6.start_mitmproxy import LocalMitmproxy

@pytest.mark.asyncio
async def test_mitmproxy_integration():
    proxy = LocalMitmproxy(port=8081, storage_dir="./test_captures")
    
    # Start proxy in background
    proxy_task = asyncio.create_task(proxy.start())
    
    # Test traffic interception
    # Make HTTP request through proxy
    # Verify content capture
    
    proxy.stop()
```

### Continuous Integration

#### GitHub Actions
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, '3.10', 3.11]
    
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        sudo apt-get update
        sudo apt-get install xvfb qt6-base-dev
        pip install -r requirements-dev.txt
    
    - name: Run tests
      run: |
        xvfb-run -a pytest --cov=osbot_pyqt6
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

## Build and Distribution

### Development Builds

#### macOS Build
```bash
# Build macOS application
python build_macos.py

# Sign with developer certificate (optional)
python build_macos.py --sign --cert-name "Developer ID Application: Your Name"

# Create DMG for distribution
# Output: dist/WebContentCapture.dmg
```

#### Windows Build
```bash
# Install PyInstaller
pip install pyinstaller

# Build Windows executable
pyinstaller --windowed --onefile integrated_main_app.py

# Create installer (requires NSIS)
makensis installer.nsi
```

#### Linux Build
```bash
# Build AppImage
python build_linux.py

# Create .deb package
python setup.py --command-packages=stdeb.command bdist_deb
```

### Release Process

#### Version Management
```python
# Update version in setup.py
setup(
    name="owasp-pyqt6",
    version="0.2.0",  # Update version
    # ...
)

# Tag release
git tag v0.2.0
git push origin v0.2.0
```

#### Release Checklist
- [ ] Update version numbers
- [ ] Run full test suite
- [ ] Update documentation
- [ ] Build for all platforms
- [ ] Test built applications
- [ ] Create release notes
- [ ] Tag and push release

## Contributing Guidelines

### Code Standards

#### Python Style
```python
# Follow PEP 8 style guide
# Use Black for formatting
# Add type hints where appropriate

def process_content(self, content: bytes, content_type: str, url: str = None) -> bytes:
    """Process content with type hints and docstring."""
    pass
```

#### Documentation
```python
class ContentReplacer:
    """
    Handles content replacement based on regex patterns.
    
    This class provides functionality to apply regex-based replacements
    to web content based on JSON configuration files.
    
    Attributes:
        data_dir: Path to configuration data directory
        replacements: List of active replacement rules
        stats: Replacement statistics and tracking
    """
```

#### Commit Messages
```bash
# Use conventional commit format
feat: add new content replacement feature
fix: resolve SSL bypass issue on Windows
docs: update architecture documentation
test: add integration tests for mitmproxy
chore: update dependencies
```

### Pull Request Process

1. **Fork & Branch**: Create feature branch from `dev`
2. **Develop**: Implement feature with tests
3. **Test**: Run full test suite locally
4. **Document**: Update relevant documentation
5. **PR**: Create pull request with description
6. **Review**: Address feedback from maintainers
7. **Merge**: Squash and merge when approved

### Issue Reporting

#### Bug Reports
```markdown
**Bug Description**
Clear description of the issue

**Steps to Reproduce**
1. Start application with: `python integrated_main_app.py`
2. Navigate to: `https://example.com`
3. Error occurs: SSL certificate error

**Expected Behavior**
Page should load without SSL errors

**Environment**
- OS: macOS 13.1
- Python: 3.10.8
- QtWebEngine: 6.4.2
- mitmproxy: 9.0.1
```

#### Feature Requests
```markdown
**Feature Description**
Ability to export captured content as PDF

**Use Case**
Researchers need to generate reports from captured content

**Proposed Implementation**
Add export functionality to FastAPI backend with PDF generation

**Additional Context**
Should support filtering by date range and content type
```

## Performance Optimization

### Profiling

#### Application Profiling
```python
# Profile application startup
import cProfile
cProfile.run('main()', 'startup_profile.stats')

# Analyze profile results
import pstats
stats = pstats.Stats('startup_profile.stats')
stats.sort_stats('cumulative').print_stats(20)
```

#### Memory Profiling
```python
# Monitor memory usage
import tracemalloc
tracemalloc.start()

# ... run application code ...

current, peak = tracemalloc.get_traced_memory()
print(f"Current memory usage: {current / 1024 / 1024:.1f} MB")
print(f"Peak memory usage: {peak / 1024 / 1024:.1f} MB")
```

### Optimization Strategies

#### Content Processing
- **Lazy Loading**: Load content replacement rules on demand
- **Caching**: Cache compiled regex patterns
- **Filtering**: Process only necessary content types
- **Batching**: Batch multiple replacements for efficiency

#### UI Responsiveness
- **Threading**: Keep UI operations on main thread
- **Async Operations**: Use async for network operations
- **Progress Indicators**: Show progress for long operations
- **Debouncing**: Debounce rapid user inputs

## Security Considerations

### Development Security

#### Code Security
- **Input Validation**: Validate all user inputs
- **Path Traversal**: Prevent directory traversal attacks
- **Injection Prevention**: Sanitize regex patterns
- **Error Handling**: Don't expose sensitive information in errors

#### SSL Bypass Security
- **Development Only**: Never use SSL bypass in production
- **Audit Logging**: Log all SSL bypass usage
- **Network Isolation**: Use in isolated development networks
- **Time-Limited**: Disable SSL bypass when not actively testing

### Secure Development Practices

#### Dependency Management
```bash
# Audit dependencies for vulnerabilities
pip-audit

# Keep dependencies updated
pip-compile --upgrade requirements.in

# Use virtual environments
python -m venv venv
```

#### Code Scanning
```bash
# Security linting
bandit -r osbot_pyqt6/

# Static analysis
semgrep --config=auto osbot_pyqt6/
```

---

*This development guide provides the foundation for contributing to and extending the Web Content Capture application while maintaining code quality and security standards.*