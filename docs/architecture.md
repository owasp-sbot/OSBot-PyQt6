# Architecture Documentation

## Overview

The Web Content Capture application follows a **Python-native architecture** that evolved from an initial Electron-based design. This document details the architectural decisions, component interactions, and technical implementation.

## Architectural Evolution

### Original Electron-Based Design (Abandoned)

The initial architecture used:
- **Electron Desktop Application**: Chromium browser UI
- **Playwright Python Engine**: Browser automation and content capture  
- **FastAPI Backend**: API endpoints and content management
- **AWS S3 Storage**: Cloud storage

#### Problems with Original Design

1. **Dual Runtime Complexity**: Required both Node.js and Python
2. **High Resource Usage**: Multiple heavyweight processes
3. **Packaging Complexity**: Difficult distribution with two runtimes  
4. **Maintenance Overhead**: Split codebase across languages
5. **Performance Issues**: Memory-heavy with sluggish performance

### Current Python-Native Architecture

The redesigned solution uses:
- **PyQt6/QtWebEngine**: Desktop application with embedded Chromium
- **mitmproxy**: Network traffic interception (replaces Playwright)
- **FastAPI Backend**: Same API structure, now integrated
- **Unified Packaging**: Single Python executable

## Component Architecture

### 1. Desktop Application Layer (PyQt6)

```python
# Main Components
WebCaptureBrowser (QMainWindow)
├── SuperBypassWebView (QWebEngineView)
│   ├── Custom QWebEngineProfile
│   ├── SSL Bypass Configuration  
│   └── Proxy Configuration
├── Navigation Toolbar
├── Status Indicators
└── Tabbed Interface
    ├── Browser Tab
    └── Capture Log Tab
```

**Key Features:**
- **QtWebEngine Browser**: Full Chromium rendering engine
- **SSL Bypass**: Multiple layers of certificate validation bypass
- **Proxy Integration**: Routes all traffic through local mitmproxy
- **Native UI**: Platform-specific controls and behaviors

### 2. Network Interception Layer (mitmproxy)

```python
# mitmproxy Architecture
LocalMitmproxy
├── DumpMaster (mitmproxy core)
├── ContentCaptureAddon
│   ├── Content Interception
│   ├── Content Replacement
│   └── Content Storage
└── Certificate Management
```

**Key Components:**

#### ContentCaptureAddon
- **Traffic Interception**: Captures ALL HTTP/HTTPS requests/responses
- **Content Processing**: Applies regex-based replacements
- **Storage Management**: Organizes captured content by flow ID
- **Metadata Generation**: Creates comprehensive request/response metadata

#### Content Replacement Engine
- **Pattern Matching**: Regex-based content modification
- **JSON Configuration**: File-based replacement rules
- **Content-Type Filtering**: Selective processing based on MIME types
- **Real-time Processing**: Modifies content before delivery to browser

### 3. Content Storage Layer

```
Storage Structure:
captures/
├── [flow-id-1]/
│   ├── metadata.json       # Request/response metadata
│   ├── response.html       # Response content (typed)
│   └── request.bin         # Request body (if present)
├── [flow-id-2]/
│   ├── metadata.json
│   ├── response.json       # JSON responses
│   └── response.bin        # Binary content
└── ...

data/
└── replacements.json       # Content replacement configuration
```

**Content Organization:**
- **Flow-based Storage**: Each request/response pair gets unique directory
- **Content-Type Aware**: Files saved with appropriate extensions
- **Metadata Rich**: Complete request/response information in JSON
- **Replacement Tracking**: Records which content was modified

### 4. Backend API Layer (FastAPI)

```python
# API Structure
FastAPI App
├── Capture Management
│   ├── POST /captures/
│   ├── GET /captures/
│   └── GET /captures/{id}
├── Content Upload
│   └── POST /captures/{id}/upload
├── System Management
│   └── POST /system/clear-all
└── CORS Configuration
```

**Integration Points:**
- **Embedded Server**: Runs within the main application
- **Content API**: Provides programmatic access to captured content
- **Upload Handling**: Supports file uploads for enhanced capture data
- **Development Interface**: Swagger UI for API exploration

## SSL Bypass Architecture

### Multi-Layer SSL Bypass Strategy

The application implements **three layers** of SSL certificate bypass:

#### 1. Environment Variables (Pre-Qt)
```python
QTWEBENGINE_CHROMIUM_FLAGS = '--ignore-certificate-errors --disable-web-security ...'
QTWEBENGINE_DISABLE_SANDBOX = '1'
```

#### 2. Command Line Arguments (Qt Application)
```python
ssl_args = [
    '--ignore-certificate-errors',
    '--ignore-ssl-errors',
    '--test-type',  # Critical for bypassing SSL validation
    '--disable-web-security',
    # ... additional flags
]
```

#### 3. Certificate Management (mitmproxy)
```python
# Custom certificate handling
- Downloads mitmproxy CA certificate
- Attempts integration with QtWebEngine certificate store
- Provides fallback mechanisms for certificate issues
```

### Why This Works

1. **Environment Variables**: Affect Chromium at the lowest level
2. **Command Line Flags**: Override default SSL behavior
3. **Test Mode**: `--test-type` puts Chromium in permissive mode
4. **Proxy Certificate**: Handles legitimate SSL interception

## Data Flow Architecture

### Request/Response Flow

```
1. User Navigation
   └── QtWebEngine Browser

2. Network Request
   └── Proxy Configuration Routes to mitmproxy

3. Traffic Interception  
   └── mitmproxy receives request
   
4. Content Processing
   ├── Original content captured
   ├── Replacement rules applied
   └── Modified content generated

5. Response Delivery
   ├── Modified content sent to browser
   └── Original + modified content stored

6. Content Storage
   ├── Organized by flow ID
   ├── Metadata generation
   └── File type detection
```

### Content Replacement Flow

```
1. Response Interception
   └── mitmproxy ContentCaptureAddon

2. Content Analysis
   ├── Content-type detection
   ├── Replacement rule matching
   └── Pattern compilation

3. Content Modification
   ├── Regex pattern application
   ├── Content encoding handling
   └── Header updates (Content-Length)

4. Delivery & Storage
   ├── Modified content → Browser
   └── Original + modified → Storage
```

## Threading Architecture

### Main Application Thread
- **PyQt6 Event Loop**: Handles UI interactions
- **Signal/Slot Communication**: Thread-safe Qt messaging
- **Timer-based Operations**: Delayed initialization and updates

### mitmproxy Thread
- **Async Event Loop**: Handles network traffic
- **Content Processing**: Applies replacements in proxy thread
- **Storage Operations**: File I/O operations

### FastAPI Thread
- **HTTP Server**: Handles API requests
- **Database Operations**: Content retrieval and management
- **Background Tasks**: Cleanup and maintenance

## Security Architecture

### Self-Contained Security Model

1. **No System Modifications**: No changes to system certificate stores
2. **Local Network Only**: All communication via localhost
3. **Process Isolation**: Each component runs in controlled environment
4. **Temporary Certificates**: mitmproxy certificates are session-specific

### SSL Security Considerations

- **Development Focus**: SSL bypass optimized for testing/development
- **Content Integrity**: Original content preserved alongside modifications
- **Audit Trail**: Complete request/response logging for security analysis
- **Configurable Bypass**: SSL handling can be adjusted per use case

## Performance Characteristics

### Memory Usage
- **Single Python Process**: ~200-400MB typical usage
- **QtWebEngine**: ~100-200MB for browser engine
- **mitmproxy**: ~50-100MB for proxy operations
- **Content Storage**: Varies based on captured content volume

### CPU Usage
- **Low Idle**: <5% CPU when not actively browsing
- **Moderate Load**: 10-20% CPU during active content capture
- **Peak Usage**: 30-50% CPU during heavy content replacement

### Storage Requirements
- **Application**: ~50MB installed size
- **Captured Content**: Varies (10KB-10MB per page typically)
- **Configuration**: <1MB for replacement rules and settings

## Scalability Considerations

### Current Limitations
- **Single User**: Designed for single-user desktop usage
- **Local Storage**: File-based storage has practical limits
- **Memory Constraints**: Large pages may consume significant memory

### Scaling Strategies
- **Database Integration**: Replace file storage with database
- **Distributed Processing**: Split capture and processing
- **Cloud Storage**: Integration with cloud storage services
- **Multi-Instance**: Support for multiple capture instances

## Extension Points

### Plugin Architecture Opportunities
1. **Content Processors**: Custom content analysis modules
2. **Storage Backends**: Alternative storage implementations
3. **UI Components**: Additional interface panels
4. **Analysis Tools**: Content analysis and reporting modules

### API Integration Points
1. **External Analysis**: Send captured content to external services
2. **Rule Management**: Programmatic replacement rule management
3. **Content Search**: Advanced search and filtering capabilities
4. **Reporting**: Generate capture reports and statistics

---

*This architecture enables powerful web content capture and modification while maintaining simplicity and reliability through a unified Python implementation.*