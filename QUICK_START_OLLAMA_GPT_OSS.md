# Quick Start: GPT-OSS via Ollama

Quick setup guide for running GPT-OSS with AppHealth.

## Method 1: Using Docker (Recommended)

### 1. Start Services with Ollama
```bash
# Start AppHealth with Ollama
docker-compose up -d

# Pull GPT-OSS model
docker-compose exec ollama ollama pull gpt-oss:20b

# Verify model is loaded
docker-compose exec ollama ollama list
```

### 2. Configure AppHealth
- Open AppHealth admin panel
- Go to Settings
- Set:
  - **LLM Provider**: `Ollama (Local LLM)`
  - **Model**: `gpt-oss:20b`
  - **Endpoint**: `http://ollama:11434/v1`

### 3. Test
Ask in AI Chat: "What services are currently down?"

## Method 2: Using Host Ollama

### 1. Install & Setup Ollama
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull GPT-OSS
ollama pull gpt-oss:20b

# Start service
ollama serve
```

### 2. Configure AppHealth
- **LLM Provider**: `Ollama (Local LLM)`
- **Model**: `gpt-oss:20b` 
- **Endpoint**: `http://host.docker.internal:11434/v1` (default)

## Troubleshooting

**Connection issues?**
```bash
# Test Ollama
curl http://localhost:11434/api/tags

# Check logs
docker-compose logs ollama
docker-compose logs backend
```

**Model not found?**
```bash
# List models
docker-compose exec ollama ollama list

# Pull if missing
docker-compose exec ollama ollama pull gpt-oss:20b
```

For detailed setup see `OLLAMA_GPT_OSS_SETUP.md`.