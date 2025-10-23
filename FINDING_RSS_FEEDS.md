# Finding RSS/Atom Feeds for Status Pages

## The Problem: Tracking Parameters

URLs with tracking parameters like:
```
https://status.docusign.com/?_ga=2.190528939...&_gl=1*1pyc5s8...&_gcl_au=...
```

These parameters:
- **`_ga`, `_gid`** = Google Analytics tracking
- **`_gl`** = Google Linker parameter
- **`_gcl_au`**, **`_gcl_aw`** = Google Click ID
- **Change constantly** and aren't needed for content

## The Solution: Clean URLs

### 1. Remove Tracking Parameters

**Before:**
```
https://status.docusign.com/?_ga=2.190528939.1633700902.1672780328-123825698.1662986922&_gl=1*1pyc5s8*_gcl_au*MTAzODgwOTc0MS4xNzYxMTA3Mzgx
```

**After:**
```
https://status.docusign.com/
```

Just take everything **before the `?`** in most cases!

### 2. Check for RSS/Atom Feeds

Most Statuspage.io-based sites have feeds:

```bash
# Check the page source for feed links
curl -s "https://status.docusign.com/" | grep -i "rss\|atom"
```

Look for lines like:
```html
<link rel="alternate" type="application/rss+xml"
      href="https://status.docusign.com/history.rss" />
<link rel="alternate" type="application/atom+xml"
      href="https://status.docusign.com/history.atom" />
```

### Common Feed URL Patterns

| Platform | Typical RSS Feed URL |
|----------|---------------------|
| **Statuspage.io** | `https://status.example.com/history.rss` |
| **Statuspage.io** | `https://status.example.com/history.atom` |
| **Statuspage.io API** | `https://status.example.com/api/v2/summary.json` |
| **Custom** | `https://status.example.com/feed.rss` |
| **Custom** | `https://status.example.com/rss` |

### 3. Test the Feed

```bash
# Test RSS feed
curl -s "https://status.docusign.com/history.rss" | head -50

# Or use the API
curl -X PUT http://localhost:8000/api/sites/SITE_ID \
  -H "Content-Type: application/json" \
  -d '{
    "feed_url": "https://status.docusign.com/history.rss",
    "parser": "auto"
  }'
```

## Quick Discovery Script

```bash
#!/bin/bash
# discover-feeds.sh - Find RSS/Atom feeds for a status page

URL=$1

if [ -z "$URL" ]; then
  echo "Usage: $0 <status-page-url>"
  exit 1
fi

# Clean URL (remove tracking params)
CLEAN_URL=$(echo "$URL" | cut -d'?' -f1)

echo "🔍 Checking: $CLEAN_URL"
echo ""

# Check for feed links in HTML
echo "📡 Looking for RSS/Atom feeds..."
curl -s "$CLEAN_URL" | grep -Eo '(rss|atom)[^"<>]*' | grep -Eo 'https?://[^"<>]+'

echo ""

# Try common patterns
echo "🧪 Testing common feed URLs..."

for FEED in \
  "${CLEAN_URL}history.rss" \
  "${CLEAN_URL}history.atom" \
  "${CLEAN_URL}api/v2/summary.json" \
  "${CLEAN_URL}feed.rss" \
  "${CLEAN_URL}feed/" \
  "${CLEAN_URL}rss"
do
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$FEED")
  if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Found: $FEED"
  fi
done

echo ""
echo "💡 Use 'auto' parser to let the system detect the format!"
```

## Real-World Examples

### DocuSign (Fixed)

**Problem URL:**
```
https://www.docusign.com/trust/system-status
```

**Discovery:**
```bash
curl -s "https://status.docusign.com/" | grep -i rss
# Found: <link rel="alternate" type="application/rss+xml"
#        href="https://status.docusign.com/history.rss" />
```

**Solution:**
```json
{
  "status_page": "https://status.docusign.com/",
  "feed_url": "https://status.docusign.com/history.rss",
  "parser": "rss"
}
```

### Slack (Fixed)

**Problem:** Wrong feed URL `https://status.slack.com/feed/`

**Discovery:**
```bash
# Try common patterns
curl -I https://slack-status.com/feed/rss  # 200 OK!
```

**Solution:**
```json
{
  "status_page": "https://status.slack.com/",
  "feed_url": "https://slack-status.com/feed/rss",
  "parser": "rss"
}
```

## Via Web UI

The dashboard has tools to help:

1. **Click "Add Site"** or **"Edit"** on existing site
2. **Enter status page URL** (with or without tracking params)
3. **Try feed URL patterns:**
   - `{status_page}/history.rss`
   - `{status_page}/api/v2/summary.json`
4. **Set parser to "auto"** - it will detect the format!
5. **Click "Poll Now"** to test immediately

## Troubleshooting

### Feed URL Returns 404

Try these alternatives:
```
/history.rss
/history.atom
/feed.rss
/feed
/rss
/api/v2/summary.json
/api/v2/status.json
```

### URL Has Auth Required

Mark as `console_only: true`:
```json
{
  "console_only": true,
  "is_active": false
}
```

### No Feed Available

Fall back to HTML parsing:
```json
{
  "feed_url": null,
  "parser": "html"
}
```

The HTML parser will:
- Use BeautifulSoup to parse the page
- Look for status indicators
- Extract incident information
- Works but less reliable than feeds

## Best Practices

1. **✅ Always prefer RSS/JSON feeds over HTML scraping**
   - More reliable
   - Structured data
   - Less likely to break

2. **✅ Use clean URLs without tracking parameters**
   - Easier to maintain
   - Consistent behavior

3. **✅ Set parser to "auto" when unsure**
   - System detects format automatically
   - Falls back if needed

4. **✅ Test with "Poll Now" after adding**
   - Verifies feed works
   - Shows actual status immediately

5. **✅ Check logs if polling fails**
   ```bash
   docker-compose logs backend | grep SITE_ID
   ```

## Summary

**For DocuSign:**
- ❌ Old: `https://www.docusign.com/trust/system-status` (HTML scraping)
- ✅ New: `https://status.docusign.com/history.rss` (RSS feed)

**Result:** Faster, more reliable, cleaner summaries!

---

**Pro Tip:** Most status pages powered by Statuspage.io (Atlassian) have feeds at `/history.rss` and `/api/v2/summary.json` 🚀
