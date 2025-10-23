# Status Dashboard

A production-ready, real-time monitoring dashboard for tracking service status pages. Monitor multiple services, track incidents, and get notified when status changes occur.

![Status Dashboard](https://img.shields.io/badge/status-production-green)
![Python](https://img.shields.io/badge/python-3.11-blue)
![React](https://img.shields.io/badge/react-18.2-blue)

## Features

- **Multi-Service Monitoring**: Track unlimited status pages from a single dashboard
- **Flexible Parsing**: Auto-detect and parse JSON feeds, RSS/Atom feeds, or HTML pages
- **Authenticated Scraping**: Support for authenticated status pages (e.g., Microsoft 365 Admin Center) using Playwright session persistence
- **Configurable Polling**: Set individual polling frequencies per service (60-3600 seconds)
- **Real-time Countdown**: See exactly when the next poll will occur with live countdown timers
- **History Tracking**: View up to 50 historical readings per service
- **Status Normalization**: Automatic normalization to standard statuses (Operational, Degraded, Incident, Maintenance, Unknown)
- **Modern UI**: Clean, responsive Tailwind CSS interface
- **Docker Ready**: Full containerization with docker-compose
- **Extensible**: Easy to add custom parsers or new services

## Quick Start

### Prerequisites

- Docker & Docker Compose (recommended)
- OR Python 3.11+ and Node.js 20+ (for local development)

### Docker Deployment (Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd appHealth
```

2. Start the application:
```bash
docker-compose up -d
```

3. Access the dashboard:
- Frontend: http://localhost
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

That's it! The dashboard will automatically load seed data with popular services.

### Local Development

#### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install Playwright browsers:
```bash
playwright install chromium
```

5. Run the backend:
```bash
cd ..  # Back to root directory
python -m uvicorn app.main:app --reload --app-dir backend
```

Backend will be available at http://localhost:8000

#### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start development server:
```bash
npm run dev
```

Frontend will be available at http://localhost:5173

## Configuration

### Environment Variables

Create a `.env` file in the root directory (see `.env.example`):

```env
# Backend
DATABASE_URL=sqlite:///./status_dashboard.db
LOG_LEVEL=INFO
DEFAULT_POLL_FREQUENCY=300
MAX_CONCURRENT_SCRAPES=5
REQUEST_TIMEOUT=30

# CORS
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

# Frontend
VITE_API_URL=http://localhost:8000/api
```

### Adding New Sites

#### Via UI

1. Click "Add Site" button
2. Fill in the form:
   - **Site ID**: Unique identifier (e.g., `aws-status`)
   - **Display Name**: Human-readable name (e.g., `AWS Service Health`)
   - **Status Page URL**: The main status page URL
   - **Feed URL** (optional): RSS/JSON feed endpoint
   - **Poll Frequency**: Seconds between polls (60-3600)
   - **Parser**: `auto`, `json`, `rss`, or `html`
   - **Active**: Enable/disable polling
   - **Console Only**: Mark if site requires authentication
   - **Use Playwright**: Enable for JavaScript-heavy pages
   - **Auth State File**: Path to saved authentication session (for authenticated pages)

#### Via seed_config.json

Add to `seed_config.json`:

```json
{
  "sites": [
    {
      "id": "my-service",
      "display_name": "My Service",
      "status_page": "https://status.myservice.com/",
      "feed_url": "https://status.myservice.com/api/v2/summary.json",
      "poll_frequency_seconds": 300,
      "parser": "auto",
      "is_active": true,
      "console_only": false,
      "use_playwright": false
    }
  ]
}
```

Then restart the backend or click "Reload" in the UI.

### Authenticated Services (Microsoft 365)

For services requiring authentication (like Microsoft 365 Admin Center), you need to set up session authentication:

#### Initial Setup

1. **Install Playwright locally** (one-time):
```bash
cd /path/to/appHealth
pip install playwright
playwright install chromium
```

2. **Run the authentication script**:
```bash
python3 authenticate_microsoft_v2.py
```

This will:
- Open a browser window
- Navigate to the Microsoft 365 Admin Center
- Wait for you to sign in with your admin account
- Save your session to `microsoft_auth_state.json`

3. **Copy the session file to Docker**:
```bash
docker cp microsoft_auth_state.json status-dashboard-backend:/app/
```

4. **Add the site** via UI or seed_config.json:
```json
{
  "id": "microsoft-365",
  "display_name": "Microsoft 365",
  "status_page": "https://admin.microsoft.com/Adminportal/Home#/servicehealth/overview",
  "feed_url": null,
  "poll_frequency_seconds": 300,
  "parser": "html",
  "is_active": true,
  "console_only": false,
  "use_playwright": true,
  "auth_state_file": "/app/microsoft_auth_state.json"
}
```

#### Re-authenticating (When Session Expires)

Your Microsoft 365 session typically lasts weeks/months. When it expires:

1. Run: `python3 authenticate_microsoft_v2.py`
2. Sign in again in the browser
3. Copy the new session: `docker cp microsoft_auth_state.json status-dashboard-backend:/app/`
4. Restart backend: `docker-compose restart backend`

The dashboard will automatically use the new session for polling.

## Architecture

### Stack

- **Backend**: Python 3.11, FastAPI, APScheduler
- **Parsers**: feedparser (RSS), BeautifulSoup4 (HTML), Playwright (dynamic pages)
- **Database**: SQLite with SQLModel ORM
- **Frontend**: React 18, Vite, Tailwind CSS
- **Deployment**: Docker, Docker Compose

### Project Structure

```
appHealth/
├── backend/
│   ├── app/
│   │   ├── api/          # REST endpoints
│   │   ├── parsers/      # JSON, RSS, HTML parsers
│   │   ├── polling/      # Scheduling engine
│   │   ├── utils/        # Normalizers, helpers
│   │   ├── models.py     # Database models
│   │   ├── config.py     # Configuration
│   │   └── main.py       # FastAPI app
│   ├── tests/            # Unit tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── services/     # API client
│   │   └── utils/        # Helpers
│   └── package.json
├── seed_config.json      # Initial site configuration
├── docker-compose.yml
└── README.md
```

## API Reference

### Endpoints

#### Sites

- `GET /api/sites` - List all sites
- `POST /api/sites` - Create new site
- `GET /api/sites/{id}` - Get site details
- `PUT /api/sites/{id}` - Update site
- `DELETE /api/sites/{id}` - Delete site
- `POST /api/sites/{id}/poll` - Trigger immediate poll
- `GET /api/sites/{id}/history?limit=50` - Get reading history

#### State

- `GET /api/state` - Get current state for all sites
- `GET /api/state/{id}` - Get state for specific site
- `POST /api/state/pause` - Pause all polling
- `POST /api/state/resume` - Resume polling
- `POST /api/state/reload` - Reload all sites

### Data Models

#### Site
```json
{
  "id": "string",
  "display_name": "string",
  "status_page": "string",
  "feed_url": "string | null",
  "poll_frequency_seconds": 300,
  "parser": "auto | json | rss | html",
  "is_active": true,
  "console_only": false,
  "use_playwright": false,
  "auth_state_file": "string | null"
}
```

#### SiteState
```json
{
  "site_id": "string",
  "display_name": "string",
  "status": "operational | degraded | incident | maintenance | unknown",
  "summary": "string",
  "last_checked_at": "datetime",
  "next_poll_at": "datetime",
  "source_type": "json | rss | html",
  "error_message": "string | null"
}
```

## Parsers

### Auto-Detection

The `auto` parser automatically detects the content type and selects the appropriate parser:

1. **JSON Parser**: Detects JSON content, parses Statuspage.io format
2. **RSS Parser**: Detects RSS/Atom feeds, extracts incidents
3. **HTML Parser**: Fallback for status pages without feeds

### Custom Parsers

To add a custom parser:

1. Create new file in `backend/app/parsers/`
2. Extend `BaseParser` class
3. Implement `parse()` and `can_parse()` methods
4. Register in `ParserFactory`

Example:
```python
from app.parsers.base import BaseParser

class CustomParser(BaseParser):
    def can_parse(self, content_type: str, content: str) -> bool:
        return "custom-format" in content_type

    async def parse(self, content: str, url: str) -> dict:
        # Your parsing logic
        return {
            "status": StatusType.OPERATIONAL,
            "summary": "Parsed summary",
            "raw_data": {},
            "last_changed_at": None,
        }
```

## Testing

### Run Backend Tests

```bash
cd backend
pytest -v
```

### Test Coverage

```bash
pytest --cov=app --cov-report=html
```

## Monitoring Pre-configured Services

The dashboard comes with 16 popular services pre-configured:

1. **Adobe Status** - HTML scraping
2. **Atlassian/Jira** - RSS feed
3. **AWS CloudFront** - RSS feed
4. **AWS EC2** - RSS feed (us-west-2 region)
5. **AWS Lambda** - RSS feed (us-west-2 region)
6. **AWS RDS** - RSS feed (us-west-2 region)
7. **Box** - JSON API
8. **DocuSign** - RSS feed
9. **Microsoft 365** - Authenticated HTML scraping (requires setup)
10. **Netlify** - RSS feed
11. **OpenAI** - RSS feed
12. **SentinelOne** - HTML scraping
13. **Slack** - RSS feed
14. **Smartsheet** - RSS feed
15. **Veeva** - HTML scraping
16. **AWS Health Dashboard** - Console only (marked for reference)

**Note**: Microsoft 365 monitoring requires one-time authentication setup (see [Authenticated Services](#authenticated-services-microsoft-365) section above).

## Troubleshooting

### Backend won't start

- Ensure Python 3.11+ is installed
- Install Playwright browsers: `playwright install chromium`
- Check database permissions

### Polls failing

- Check network connectivity
- Verify feed URLs are accessible
- Review logs: `docker-compose logs backend`
- Some sites may require rate limiting (increase `poll_frequency_seconds`)
- For authenticated services: Check if session has expired (see [Re-authenticating](#re-authenticating-when-session-expires))

### Microsoft 365 shows "Authentication required"

- Your session may have expired
- Re-run the authentication script: `python3 authenticate_microsoft_v2.py`
- Copy the new session file: `docker cp microsoft_auth_state.json status-dashboard-backend:/app/`
- Restart backend: `docker-compose restart backend`

### Microsoft 365 showing incorrect status

- The parser distinguishes between:
  - **Advisories** (informational) → Reported as OPERATIONAL ✅
  - **Degraded** (performance issues) → Reported as DEGRADED ⚠️
  - **Incidents** (major outages) → Reported as INCIDENT 🔴
- If you see many advisories but operational status, this is correct behavior

### Frontend not loading

- Check if backend is running on port 8000
- Verify CORS settings in backend config
- Clear browser cache

### Docker issues

- Ensure ports 80 and 8000 are available
- Check Docker daemon is running
- Try rebuilding: `docker-compose build --no-cache`

## Production Deployment

### Security Considerations

1. **Use HTTPS**: Configure reverse proxy (nginx, Traefik)
2. **Restrict CORS**: Set specific allowed origins
3. **Rate Limiting**: Implement at reverse proxy level
4. **Database Backups**: Regular backups of SQLite file
5. **Secrets Management**: Use environment variables, not hardcoded values

### Scaling

- For high volume: Switch from SQLite to PostgreSQL
- Use Redis for caching frequent reads
- Deploy multiple backend instances behind load balancer
- Consider using Celery instead of APScheduler for distributed polling

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create feature branch
3. Add tests for new features
4. Ensure tests pass
5. Submit pull request

## Support

For issues and questions:
- GitHub Issues: [Link to issues]
- Documentation: This README
- API Docs: http://localhost:8000/docs

## Acknowledgments

- Status page data providers
- FastAPI framework
- React community
- Tailwind CSS
