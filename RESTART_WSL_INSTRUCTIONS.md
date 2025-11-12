# WSL Memory Configuration for GPT-OSS:20b

## Steps to Apply New Memory Settings:

1. **Save your work** in any open WSL terminals

2. **Stop Docker Compose** (if not already done):
   ```bash
   cd ~/appHealth
   docker-compose down
   ```

3. **Exit WSL** and close all WSL terminals

4. **In Windows PowerShell (as Administrator)**, run:
   ```powershell
   wsl --shutdown
   ```

5. **Wait 10 seconds**, then restart WSL by opening a new Ubuntu terminal

6. **Verify the new memory allocation**:
   ```bash
   free -h
   ```
   You should see ~32GB total memory

7. **Restart AppHealth with Ollama**:
   ```bash
   cd ~/appHealth
   docker-compose up -d
   ```

8. **Pull GPT-OSS:20b** (will now work with increased memory):
   ```bash
   docker-compose exec ollama ollama pull gpt-oss:20b
   ```

9. **Verify the model loads**:
   ```bash
   docker-compose exec ollama ollama run gpt-oss:20b "Hello"
   ```

## What Changed:

- Created `~/.wslconfig` with:
  - **Memory**: 32GB (from 8GB) - enough for GPT-OSS:20b
  - **Swap**: 16GB additional virtual memory
  - **Processors**: 8 cores
  
This gives Ollama ~48GB total (32GB RAM + 16GB swap) to work with, which is plenty for the 13.1GB model.

## After Restart:

The GPT-OSS:20b model will load successfully and your chat will work with the full model instead of getting memory errors.