# Content Replacement System

## Overview

The Content Replacement System provides **real-time regex-based modification** of web content as it passes through the mitmproxy. This enables powerful content transformation capabilities for testing, analysis, and research purposes.

## How It Works

### Architecture

```
Web Request → mitmproxy → ContentReplacer → Modified Response → Browser
                ↓
        Original + Modified Content Saved to Storage
```

1. **Traffic Interception**: mitmproxy captures all HTTP/HTTPS responses
2. **Content Analysis**: ContentReplacer checks content type and replacement rules
3. **Pattern Matching**: Enabled regex patterns are applied to content
4. **Content Modification**: Matching patterns are replaced according to rules
5. **Response Update**: Modified content is sent to browser with updated headers
6. **Storage**: Both original and modified content are saved for analysis

## Configuration

### JSON Configuration File

The replacement system uses `./data/replacements.json` for configuration:

```json
{
  "info": {
    "description": "Content replacement configuration for mitmproxy",
    "created": "2025-01-22T15:30:00",
    "format": "Each replacement has: pattern (regex), replacement (string), flags (optional), content_types (optional)"
  },
  "replacements": [
    {
      "name": "Example: Replace 'Google' with 'MODIFIED'",
      "pattern": "\\bGoogle\\b",
      "replacement": "MODIFIED",
      "flags": ["IGNORECASE"],
      "content_types": ["text/html", "application/json"],
      "enabled": false,
      "description": "Example replacement - disabled by default"
    }
  ],
  "stats": {
    "total_processed": 0,
    "total_replaced": 0,
    "last_updated": null
  }
}
```

### Configuration Fields

#### Replacement Rule Structure

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Human-readable name for the rule |
| `pattern` | string | Yes | Regex pattern to match |
| `replacement` | string | Yes | Replacement text (supports backreferences) |
| `flags` | array | No | Regex flags (IGNORECASE, MULTILINE, etc.) |
| `content_types` | array | No | MIME types to process (empty = all text types) |
| `enabled` | boolean | No | Whether the rule is active (default: true) |
| `description` | string | No | Documentation for the rule |

## Regex Patterns

### Basic Text Replacement

```json
{
  "name": "Replace Company Name",
  "pattern": "\\bAcme Corp\\b",
  "replacement": "Modified Corp",
  "flags": ["IGNORECASE"],
  "enabled": true
}
```

### URL Replacement

```json
{
  "name": "Redirect URLs",
  "pattern": "https://example\\.com",
  "replacement": "https://modified-example.com",
  "content_types": ["text/html", "text/css"],
  "enabled": true
}
```

### HTML Injection

```json
{
  "name": "Add Warning Banner",
  "pattern": "(<body[^>]*>)",
  "replacement": "\\1<div style='background:red;color:white;padding:10px;text-align:center'>⚠️ CONTENT MODIFIED ⚠️</div>",
  "content_types": ["text/html"],
  "enabled": true
}
```

### Advanced Pattern Matching

```json
{
  "name": "Email Obfuscation",
  "pattern": "([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})",
  "replacement": "\\1[AT]\\2",
  "flags": ["IGNORECASE"],
  "content_types": ["text/html", "text/plain"],
  "enabled": true
}
```

## Regex Flags

### Supported Flags

| Flag | Description | Usage |
|------|-------------|-------|
| `IGNORECASE` | Case-insensitive matching | Most common for text replacement |
| `MULTILINE` | `^` and `$` match line boundaries | For multi-line content |
| `DOTALL` | `.` matches newline characters | For patterns spanning lines |
| `VERBOSE` | Ignore whitespace and allow comments | For complex patterns |
| `ASCII` | ASCII-only matching | For ASCII text processing |
| `LOCALE` | Locale-aware matching | For localized content |

### Example Usage

```json
{
  "name": "Multi-line Pattern",
  "pattern": "^Error:\\s*(.+)$",
  "replacement": "⚠️ Alert: \\1",
  "flags": ["MULTILINE", "IGNORECASE"],
  "enabled": true
}
```

## Content Type Filtering

### Supported Content Types

The system automatically processes these content types:

- `text/html` - HTML pages
- `text/plain` - Plain text
- `text/css` - Stylesheets
- `application/javascript` - JavaScript files
- `application/json` - JSON responses
- `text/javascript` - Legacy JavaScript MIME type
- `application/xml` - XML documents
- `text/xml` - XML text

### Content Type Examples

#### HTML Only
```json
{
  "content_types": ["text/html"],
  "pattern": "<title>([^<]+)</title>",
  "replacement": "<title>Modified: \\1</title>"
}
```

#### JSON API Responses
```json
{
  "content_types": ["application/json"],
  "pattern": "\"status\":\\s*\"success\"",
  "replacement": "\"status\": \"modified\""
}
```

#### Multiple Types
```json
{
  "content_types": ["text/html", "text/css", "application/javascript"],
  "pattern": "company-logo\\.png",
  "replacement": "modified-logo.png"
}
```

## Advanced Examples

### 1. Social Media Content Modification

```json
{
  "name": "Twitter Handle Replacement",
  "pattern": "@([a-zA-Z0-9_]+)",
  "replacement": "@Modified_\\1",
  "content_types": ["text/html", "application/json"],
  "flags": ["IGNORECASE"],
  "enabled": true,
  "description": "Modifies Twitter handles for privacy"
}
```

### 2. Price Modification for Testing

```json
{
  "name": "Price Testing",
  "pattern": "\\$([0-9,]+\\.\\d{2})",
  "replacement": "$999.99",
  "content_types": ["text/html"],
  "enabled": false,
  "description": "Replace all prices with test value"
}
```

### 3. A/B Testing Content

```json
{
  "name": "Headline A/B Test",
  "pattern": "<h1>([^<]+)</h1>",
  "replacement": "<h1>🚀 \\1 (Version B)</h1>",
  "content_types": ["text/html"],
  "enabled": true,
  "description": "Modify headlines for A/B testing"
}
```

### 4. Security Header Injection

```json
{
  "name": "Add Security Notice",
  "pattern": "(<head[^>]*>)",
  "replacement": "\\1<meta name='modified' content='true'><style>.security-notice{position:fixed;top:0;left:0;right:0;background:#ff0000;color:#fff;text-align:center;padding:5px;z-index:9999;}</style>",
  "content_types": ["text/html"],
  "enabled": false,
  "description": "Adds security modification notice"
}
```

## Testing and Debugging

### Rule Testing Process

1. **Create Test Rule**: Add a simple replacement rule
2. **Enable Rule**: Set `"enabled": true`
3. **Navigate to Target**: Browse to a site with matching content
4. **Verify Modification**: Check browser for changes
5. **Check Logs**: Look for `🔄` indicators in console
6. **Review Captured Content**: Examine saved files in `./captures/`

### Debugging Tips

#### Console Output
```bash
🔄 Applied replacement 'Test Rule' to https://example.com/
📡 Captured: GET https://example.com/ → 200 (text/html) 🔄
```

#### Metadata Inspection
```json
{
  "response": {
    "content_modified": true,
    "status_code": 200,
    "content_type": "text/html"
  }
}
```

### Common Issues

#### Pattern Not Matching
- **Check Escaping**: Use `\\` for literal backslashes
- **Test Pattern**: Use online regex testers
- **Verify Content Type**: Ensure rule applies to correct MIME type

#### Replacement Not Working
- **Check Flags**: Add `IGNORECASE` for case-insensitive matching
- **Verify Enable Status**: Ensure `"enabled": true`
- **Check Content**: View raw content in captured files

#### Performance Issues
- **Limit Patterns**: Avoid overly complex regex patterns
- **Filter Content Types**: Only process necessary MIME types
- **Disable Unused Rules**: Set `"enabled": false` for inactive rules

## Statistics and Monitoring

### Replacement Statistics

The system tracks:
- `total_processed`: Total responses processed
- `total_replaced`: Total responses modified
- `active_replacements`: Number of enabled rules
- `last_updated`: Timestamp of last modification

### Monitoring Tools

#### Console Logs
- `🔄` indicator for modified content
- Pattern application notifications  
- Error messages for failed replacements

#### Capture Metadata
- `content_modified` flag in metadata.json
- Original content preservation
- Replacement tracking per flow

## Best Practices

### Rule Management

1. **Use Descriptive Names**: Clear rule identification
2. **Add Descriptions**: Document rule purpose and usage
3. **Test Incrementally**: Enable one rule at a time for testing
4. **Backup Configuration**: Keep copies of working configurations
5. **Version Control**: Track changes to replacement rules

### Pattern Design

1. **Specific Patterns**: Avoid overly broad matches
2. **Escape Special Characters**: Properly escape regex metacharacters
3. **Use Word Boundaries**: `\\b` for precise word matching
4. **Test Extensively**: Verify patterns with various content
5. **Consider Performance**: Avoid catastrophic backtracking

### Content Safety

1. **Preserve Functionality**: Avoid breaking page functionality
2. **Test Thoroughly**: Verify modifications don't cause errors
3. **Monitor Impact**: Check for unintended side effects
4. **Backup Original**: Always preserve original content
5. **Document Changes**: Clear documentation of modifications

---

*The Content Replacement System provides powerful real-time content modification capabilities while maintaining safety and reliability through comprehensive configuration options and monitoring.*