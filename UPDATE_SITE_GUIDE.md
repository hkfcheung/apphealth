# How to Update a Site Configuration

This guide shows you how to update site configurations, specifically fixing the Slack feed URL.

## Method 1: Via Web UI (Easiest) ✨

1. **Open the dashboard**: http://localhost

2. **Find the Slack card** (it will show an error)

3. **Click the "Edit" button** on the Slack card

4. **Update the Feed URL** to:
   ```
   https://slack-status.com/feed/rss
   ```

5. **Click "Update Site"**

6. **Wait ~2 seconds** and you'll see the site update

The site will be re-polled immediately with the new URL!

---

## Method 2: Via API (For Scripts) 🔧

### Using curl:

```bash
curl -X PUT http://localhost:8000/api/sites/slack \
  -H "Content-Type: application/json" \
  -d '{
    "id": "slack",
    "display_name": "Slack",
    "status_page": "https://status.slack.com/",
    "feed_url": "https://slack-status.com/feed/rss",
    "poll_frequency_seconds": 300,
    "parser": "rss",
    "is_active": true,
    "console_only": false
  }'
```

### Using Python:

```python
import requests

url = "http://localhost:8000/api/sites/slack"
data = {
    "id": "slack",
    "display_name": "Slack",
    "status_page": "https://status.slack.com/",
    "feed_url": "https://slack-status.com/feed/rss",
    "poll_frequency_seconds": 300,
    "parser": "rss",
    "is_active": True,
    "console_only": False
}

response = requests.put(url, json=data)
print(response.json())
```

### Using JavaScript/Node:

```javascript
fetch('http://localhost:8000/api/sites/slack', {
  method: 'PUT',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    id: 'slack',
    display_name: 'Slack',
    status_page: 'https://status.slack.com/',
    feed_url: 'https://slack-status.com/feed/rss',
    poll_frequency_seconds: 300,
    parser: 'rss',
    is_active: true,
    console_only: false
  })
})
.then(r => r.json())
.then(console.log);
```

---

## Method 3: Via Config File + Reload (For Bulk Updates) 📝

1. **Edit the seed config**:
   ```bash
   nano seed_config.json
   ```

2. **Find the Slack entry** and update `feed_url`:
   ```json
   {
     "id": "slack",
     "display_name": "Slack",
     "status_page": "https://status.slack.com/",
     "feed_url": "https://slack-status.com/feed/rss",
     "poll_frequency_seconds": 300,
     "parser": "rss",
     "is_active": true,
     "console_only": false
   }
   ```

3. **Update the database directly** (if already loaded):
   ```bash
   # Delete the old Slack site
   curl -X DELETE http://localhost:8000/api/sites/slack

   # Recreate with new config
   curl -X POST http://localhost:8000/api/sites \
     -H "Content-Type: application/json" \
     -d @- << 'EOF'
   {
     "id": "slack",
     "display_name": "Slack",
     "status_page": "https://status.slack.com/",
     "feed_url": "https://slack-status.com/feed/rss",
     "poll_frequency_seconds": 300,
     "parser": "rss",
     "is_active": true,
     "console_only": false
   }
   EOF
   ```

4. **Or restart the backend** to reload from config:
   ```bash
   docker-compose restart backend
   ```

---

## Verify the Update

After updating, verify it worked:

### Check via API:
```bash
curl http://localhost:8000/api/sites/slack | jq
```

### Check via Web UI:
1. Open http://localhost
2. Find the Slack card
3. Click "Poll Now" to test immediately
4. The error should be gone!

### View Logs:
```bash
docker-compose logs -f backend | grep slack
```

You should see:
```
Successfully parsed https://slack-status.com/feed/rss using rss parser
Poll complete for slack: StatusType.OPERATIONAL via rss
```

---

## Quick Reference: Common Updates

### Change Poll Frequency
```bash
curl -X PUT http://localhost:8000/api/sites/slack \
  -H "Content-Type: application/json" \
  -d '{"poll_frequency_seconds": 600, ...other fields}'
```

### Disable/Enable a Site
```bash
# Disable
curl -X PUT http://localhost:8000/api/sites/slack \
  -H "Content-Type: application/json" \
  -d '{"is_active": false, ...other fields}'

# Enable
curl -X PUT http://localhost:8000/api/sites/slack \
  -H "Content-Type: application/json" \
  -d '{"is_active": true, ...other fields}'
```

### Change Parser Type
```bash
curl -X PUT http://localhost:8000/api/sites/slack \
  -H "Content-Type: application/json" \
  -d '{"parser": "auto", ...other fields}'
```

Available parsers: `auto`, `json`, `rss`, `html`

---

## Troubleshooting

### "Site not found" error
Make sure you're using the correct site ID (e.g., `slack` not `Slack`)

### Changes not appearing
- Refresh the browser (F5)
- Wait 10 seconds for auto-refresh
- Check backend logs: `docker-compose logs backend`

### Still getting errors
1. Test the feed URL directly:
   ```bash
   curl -I https://slack-status.com/feed/rss
   ```
2. Check if it returns 200 OK
3. Try changing parser to `auto` to let the system detect

---

## Summary

**Recommended Method**: Use the Web UI (Method 1) - it's the easiest!

The Edit button is now available on every site card. Just click, update, and save!
