# LLM Intelligence System - Implementation Guide

## Overview

A comprehensive advisory analysis and AI chat system that intelligently filters and prioritizes service advisories based on your organization's specific modules/packages.

## ✅ What's Implemented (Backend Complete)

### 1. Database Models
- **SiteModule**: Track which modules you care about per site (e.g., "Exchange Online", "Teams")
- **Advisory**: Store and analyze service advisories with LLM-powered classification
- **ChatMessage**: Admin chat history for querying dashboard data
- **AppSettings**: Extended with LLM configuration (provider, API key, model)

### 2. LLM Service (`app/services/llm.py`)
**Multi-Provider Support:**
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude 3.5 Sonnet, etc.)
- Fallback (keyword-based when no API key configured)

**Capabilities:**
- **Advisory Analysis**: Determines criticality (high/medium/low) and relevance to your modules
- **Chat Interface**: Contextual conversations about status data
- **Automatic Fallback**: Works without API keys using basic keyword matching

### 3. API Endpoints (`/api/intelligence/`)

**Module Management:**
- `GET /sites/{site_id}/modules` - Get configured modules
- `POST /sites/{site_id}/modules` - Add module to monitor
- `PATCH /modules/{module_id}` - Enable/disable module
- `DELETE /modules/{module_id}` - Remove module

**Advisory Management:**
- `GET /sites/{site_id}/advisories` - Get advisories for a site
- `GET /advisories/summary` - Dashboard summary of all advisories

**AI Chat:**
- `POST /chat` - Chat with AI about dashboard data
- `GET /chat/history` - Retrieve chat history
- `DELETE /chat/history` - Clear chat history

**Demo/Testing:**
- `POST /analyze-demo` - Test advisory analysis

### 4. Admin Settings Updated
- LLM Provider selection (openai/anthropic/none)
- API Key storage
- Model selection

### 5. Database Migrations
All tables created and ready:
```
✓ site_modules
✓ advisories
✓ chat_messages
✓ app_settings (with LLM fields)
```

## 🚧 What Needs to Be Completed

### Frontend Components (Not Yet Built)

#### 1. Admin Settings UI Enhancement
**File**: `frontend/src/components/AdminSettingsModal.jsx`

Add LLM configuration section:
```jsx
<div className="mb-6">
  <h3>AI Intelligence</h3>

  {/* Provider Selection */}
  <select value={llm_provider}>
    <option value="">None (Basic Keywords Only)</option>
    <option value="openai">OpenAI</option>
    <option value="anthropic">Anthropic</option>
  </select>

  {/* API Key */}
  <input type="password" placeholder="API Key" />

  {/* Model Selection */}
  <select value={llm_model}>
    {/* OpenAI models */}
    <option value="gpt-4">GPT-4</option>
    <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>

    {/* Anthropic models */}
    <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet</option>
  </select>
</div>
```

#### 2. Module Configuration UI
**File**: `frontend/src/components/ModuleConfigModal.jsx` (NEW)

Interface to configure which modules/packages to monitor per site:
- Input field to add module names
- List of configured modules with enable/disable toggles
- Suggested modules based on service (e.g., M365 → Exchange, Teams, SharePoint)

#### 3. Advisory Display in Site Cards
**File**: Update `frontend/src/components/SiteCard.jsx`

Add advisory section showing:
- Count of affecting advisories with criticality badges
- Expandable list of recent advisories
- Criticality indicators (high=red, medium=yellow, low=blue)
- "Affects Us" badge when relevant modules mentioned

#### 4. Chat Interface
**File**: `frontend/src/components/AdminChatPanel.jsx` (NEW)

Right-side sliding panel with:
- Chat message list
- Input field for questions
- Context-aware responses
- Example queries:
  - "Summarize today's outages"
  - "Does the AWS incident affect us?"
  - "What modules are impacted?"

## 📋 Implementation Roadmap

### Phase 1: Basic Module Configuration (2-3 hours)
1. Create Module Config modal component
2. Add "Configure Modules" button to site cards
3. Connect to `/intelligence/sites/{id}/modules` API
4. Test adding/removing modules

### Phase 2: Admin Settings Enhancement (1 hour)
1. Add LLM configuration section to AdminSettingsModal
2. Add provider selection dropdown
3. Add API key input field
4. Add model selection based on provider
5. Update API calls to include LLM settings

### Phase 3: Advisory Integration (3-4 hours)
1. Create advisory parser service (extract from RSS/HTML/JSON)
2. Integrate into polling scheduler
3. Call `LLMService.analyze_advisory()` for each advisory
4. Store in database
5. Display in site cards

### Phase 4: Chat Interface (2-3 hours)
1. Create sliding chat panel component
2. Add chat button to header
3. Connect to `/intelligence/chat` API
4. Display message history
5. Add example query buttons

## 🔧 Configuration Examples

### For Microsoft 365:
**Modules to Configure:**
- Exchange Online
- Teams
- SharePoint Online
- OneDrive for Business
- Outlook
- Azure Active Directory

### For AWS:
**Modules to Configure:**
- EC2
- S3
- Lambda
- CloudFront
- RDS
- ECS

### For Slack:
**Modules to Configure:**
- Messaging
- Calls
- Huddles
- Notifications
- Search

## 🎯 How It Works (End-to-End)

### Scenario: Microsoft 365 Advisory

1. **Status Page Updates**:
   - Dashboard polls M365 status page
   - Finds new advisory: "Exchange Online experiencing delays"

2. **LLM Analysis**:
   ```python
   result = await LLMService.analyze_advisory(
       title="Exchange Online experiencing delays",
       description="Users may experience delays...",
       severity="Medium",
       configured_modules=["Exchange Online", "Teams", "SharePoint"],
       service_name="Microsoft 365"
   )
   # Returns:
   # {
   #   "criticality": "high",
   #   "affects_us": True,
   #   "affected_modules": ["Exchange Online"],
   #   "relevance_reason": "Directly impacts configured Exchange Online module"
   # }
   ```

3. **Storage**:
   - Advisory saved to database
   - `affects_us=True` flagged
   - `criticality="high"` assigned

4. **Display**:
   - Site card shows "🔴 1 High Priority Advisory"
   - Admin can see "Affects: Exchange Online"
   - Click to expand full details

5. **Chat Query**:
   ```
   User: "What's affecting us today?"
   AI: "There is 1 high-priority issue affecting Exchange Online.
        Users are experiencing email delays. This was detected 2 hours ago
        and is currently being investigated by Microsoft."
   ```

## 💡 Best Practices

### Module Naming
- Match vendor terminology exactly ("Exchange Online" not "Exchange")
- Be specific ("Teams Calling" vs just "Teams")
- Include component names when relevant

### LLM Provider Selection
- **OpenAI**: Better for general understanding, cheaper
- **Anthropic**: Better technical analysis, more context
- **Fallback**: Works without API key, basic keyword matching

### Criticality Guidelines (LLM-Assigned)
- **High**: Service down, data loss, security issues
- **Medium**: Degraded performance, partial outages
- **Low**: Informational notices, scheduled maintenance

## 🔐 Security Notes

- API keys stored encrypted in database
- Never expose keys in frontend responses
- Use environment variables in production
- Rotate API keys periodically

## 📊 Current Status

| Component | Status | Notes |
|-----------|--------|-------|
| Database Models | ✅ Complete | All tables created |
| LLM Service | ✅ Complete | OpenAI, Anthropic, fallback |
| API Endpoints | ✅ Complete | 10+ endpoints ready |
| Admin Settings Backend | ✅ Complete | LLM config stored |
| Module Config UI | ❌ Not Started | Need React component |
| Advisory Display | ❌ Not Started | Need site card updates |
| Chat UI | ❌ Not Started | Need chat panel component |
| Advisory Parser | ❌ Not Started | Need service to extract advisories |

## 🚀 Quick Start (Testing)

### 1. Enable LLM (Admin Panel)
Navigate to Admin settings and configure:
- Provider: "openai" or "anthropic"
- API Key: Your API key
- Model: "gpt-4" or "claude-3-5-sonnet-20241022"

### 2. Configure Modules (API)
```bash
curl -X POST http://localhost:8000/api/intelligence/sites/microsoft-365/modules \
  -H "Content-Type: application/json" \
  -d '{
    "site_id": "microsoft-365",
    "module_name": "Exchange Online",
    "enabled": true
  }'
```

### 3. Test Analysis
```bash
curl -X POST http://localhost:8000/api/intelligence/analyze-demo
```

### 4. Test Chat
```bash
curl -X POST http://localhost:8000/api/intelligence/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What services are down today?"}'
```

## 📝 Next Steps

1. **Restart Backend**: `docker-compose restart backend`
2. **Test API Endpoints**: Use curl or Postman to test endpoints
3. **Build Frontend Components**: Start with Module Config UI
4. **Integrate Advisory Parsing**: Add to polling scheduler
5. **Deploy Chat Interface**: Create sliding panel component

The foundation is solid and ready for frontend integration!
