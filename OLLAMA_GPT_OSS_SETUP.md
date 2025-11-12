# Setting up GPT-OSS via Ollama for AppHealth AI Chat

This guide explains how to configure AppHealth to use GPT-OSS models through Ollama while maintaining SQLite schema context for accurate queries.

## Overview

AppHealth already has built-in Ollama support that expects an OpenAI-compatible API. You can use this with GPT-OSS models by running them through Ollama.

## Prerequisites

- Ollama installed on your system
- Access to GPT-OSS models
- AppHealth running (either locally or in Docker)

## Step 1: Install and Pull GPT-OSS Model

### Install Ollama (if not already installed)

```bash
# On macOS
brew install ollama

# On Linux
curl -fsSL https://ollama.ai/install.sh | sh

# On Windows
# Download from https://ollama.ai/download
```

### Pull GPT-OSS Model

```bash
# Pull the 20B model
ollama pull gpt-oss:20b

# Or pull the 120B model (requires more resources)
ollama pull gpt-oss:120b

# List available models to verify
ollama list
```

### Start Ollama Service

```bash
# Start Ollama (usually starts automatically)
ollama serve

# Verify it's running
curl http://localhost:11434/api/tags
```

## Step 2: Configure AppHealth

### Option A: Through Admin UI

1. Navigate to your AppHealth admin panel
2. Go to **Settings** 
3. Configure the following:
   - **LLM Provider**: Select `Ollama (Local LLM)`
   - **Model**: Enter `gpt-oss:20b` (or `gpt-oss:120b`)
   - **Ollama Endpoint**: Leave default `http://host.docker.internal:11434/v1` or adjust based on your setup:
     - **Local development**: `http://localhost:11434/v1`
     - **Docker on same host**: `http://host.docker.internal:11434/v1`
     - **Custom setup**: `http://your-ollama-host:11434/v1`

### Option B: Direct Database Update

```sql
UPDATE AppSettings 
SET value = 'ollama' 
WHERE key = 'llm_provider';

UPDATE AppSettings 
SET value = 'gpt-oss:20b' 
WHERE key = 'llm_model';

-- Set Ollama endpoint (optional, defaults to host.docker.internal:11434/v1)
UPDATE AppSettings 
SET value = 'http://localhost:11434/v1' 
WHERE key = 'llm_api_key';
```

### Option C: Environment Variables

```env
LLM_PROVIDER=ollama
LLM_MODEL=gpt-oss:20b
LLM_API_KEY=http://localhost:11434/v1  # Ollama endpoint
```

## Step 3: Docker Setup (if using Docker)

### Option A: Add Ollama to Docker Compose

Add this service to your `docker-compose.yml`:

```yaml
services:
  # ... existing services

  ollama:
    image: ollama/ollama:latest
    container_name: apphealth_ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0
    restart: unless-stopped
    # For GPU support (optional)
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: 1
    #           capabilities: [gpu]

volumes:
  ollama_data:
  # ... existing volumes
```

Then pull the model inside the container:

```bash
# Start the services
docker-compose up -d

# Pull GPT-OSS model in the Ollama container
docker-compose exec ollama ollama pull gpt-oss:20b

# Update AppHealth settings to use container name
# Endpoint: http://ollama:11434/v1
```

### Option B: Use Host Ollama (Easier)

Keep Ollama running on your host machine and use the default endpoint configuration. AppHealth will connect via `host.docker.internal:11434`.

## Step 4: Verification

### Test the Configuration

1. **Check Settings**:
   ```sql
   SELECT key, value 
   FROM AppSettings 
   WHERE key IN ('llm_provider', 'llm_model', 'llm_api_key');
   ```

2. **Test Ollama Connection**:
   ```bash
   # Test from host
   curl http://localhost:11434/v1/models

   # Test from Docker (if using container setup)
   docker-compose exec backend curl http://ollama:11434/v1/models
   ```

3. **Test AppHealth Chat**:
   - Open the Admin panel
   - Navigate to AI Chat
   - Ask: "What services are currently down?"
   - Should respond using GPT-OSS model

### Monitor for Issues

```bash
# Check backend logs
docker-compose logs -f backend

# Check Ollama logs
docker-compose logs -f ollama  # if using container
# or
journalctl -u ollama  # if using systemd service
```

## Configuration Details

### How It Works

1. **Chat Flow**: User question → AppHealth → Ollama API → GPT-OSS model → Response
2. **Schema Context**: AppHealth automatically includes database schema in prompts
3. **SQL Generation**: Uses custom SQL backend when Ollama is configured
4. **Error Handling**: Falls back to simple responses if Ollama is unavailable

### API Compatibility

AppHealth expects Ollama to provide OpenAI-compatible endpoints:
- **Chat**: `POST /v1/chat/completions`
- **Models**: `GET /v1/models`

The system automatically formats requests as:

```json
{
  "model": "gpt-oss:20b",
  "messages": [
    {"role": "system", "content": "Database schema and context..."},
    {"role": "user", "content": "User question"}
  ],
  "temperature": 0.1,
  "max_tokens": 1500
}
```

### Performance Considerations

- **GPT-OSS 20B**: Requires ~16GB RAM, faster inference
- **GPT-OSS 120B**: Requires ~64GB RAM, better quality
- **GPU Acceleration**: Recommended for better performance
- **Temperature**: Set to 0.1 to minimize hallucinations for data queries

## Troubleshooting

### Common Issues

1. **Connection Refused**:
   ```
   Error: Cannot connect to Ollama at http://host.docker.internal:11434
   ```
   - Check if Ollama is running: `ollama list`
   - Verify port 11434 is accessible
   - Update endpoint configuration if needed

2. **Model Not Found**:
   ```
   Error: model "gpt-oss:20b" not found
   ```
   - Pull the model: `ollama pull gpt-oss:20b`
   - Check available models: `ollama list`

3. **Slow Responses**:
   - GPT-OSS models are large, first request may be slow
   - Consider using GPU acceleration
   - Monitor system resources (RAM/GPU usage)

4. **Generic Fallback Responses**:
   - Check backend logs for specific error messages
   - Verify Ollama endpoint is correct
   - Ensure model is loaded: `ollama show gpt-oss:20b`

### Debug Commands

```bash
# Test Ollama directly
curl -X POST http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-oss:20b",
    "messages": [{"role": "user", "content": "Hello"}]
  }'

# Check model status
ollama show gpt-oss:20b

# Monitor resource usage
ollama ps
```

## Advanced Configuration

### Custom Model Settings

You can create a custom Modelfile to adjust GPT-OSS behavior:

```dockerfile
# Create Modelfile
FROM gpt-oss:20b

# Customize for AppHealth
TEMPLATE """{{ if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{ if .Prompt }}<|im_start|>user
{{ .Prompt }}<|im_end|>
{{ end }}<|im_start|>assistant
"""

PARAMETER temperature 0.1
PARAMETER top_p 0.9
PARAMETER top_k 40
```

```bash
# Create custom model
ollama create apphealth-gpt-oss -f Modelfile

# Use in AppHealth
# Model: apphealth-gpt-oss
```

### Load Balancing (Multiple Instances)

For high availability, you can run multiple Ollama instances:

```yaml
# docker-compose.yml
services:
  ollama-1:
    image: ollama/ollama:latest
    ports: ["11434:11434"]
    
  ollama-2:
    image: ollama/ollama:latest
    ports: ["11435:11434"]
    
  # Use a load balancer or update endpoint rotation in AppHealth
```

The GPT-OSS models through Ollama will provide high-quality responses while maintaining the SQLite schema context needed for accurate data queries.