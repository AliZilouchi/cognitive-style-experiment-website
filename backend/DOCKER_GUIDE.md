# Sepid RAG: Docker quick start

## Requirements

- Docker Desktop with the Docker Compose plugin
- At least 8 GB of memory available to Docker is recommended for the first build and model load
- A Groq API key

The first startup downloads the pinned multilingual E5 embedding model. Its Hugging Face cache and the generated corpus index are stored in Docker volumes, so later starts are faster.

## Windows PowerShell

Open PowerShell inside the extracted `sepid-rag-docker-final` directory:

```powershell
Copy-Item .env.docker.example .env
notepad .env
```

Replace `REPLACE_WITH_YOUR_GROQ_API_KEY` with the real key. Do not add quotation marks around the key. Then run:

```powershell
docker compose up --build -d
docker compose logs -f rag-api
```

Wait until the logs show that Uvicorn is running. Stop following the logs with `Ctrl+C`; this does not stop the container.

Check the backend:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Test a Persian question:

```powershell
$body = @{
  session_id = "docker-pilot-001"
  task_id = "task_1"
  message = "هتل صدف برای چند نفر مناسب است و هزینه هر شب آن چقدر است؟"
  history = @()
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8000/chat `
  -ContentType "application/json; charset=utf-8" `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
```

The interactive API page is available at <http://localhost:8000/docs>.

## Linux, macOS, or WSL

```bash
cp .env.docker.example .env
```

Edit `.env`, replace `REPLACE_WITH_YOUR_GROQ_API_KEY`, and run:

```bash
docker compose up --build -d
docker compose logs -f rag-api
```

Health check:

```bash
curl http://localhost:8000/health
```

Chat check:

```bash
curl -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "session_id": "docker-pilot-001",
    "task_id": "task_1",
    "message": "هتل صدف برای چند نفر مناسب است و هزینه هر شب آن چقدر است؟",
    "history": []
  }'
```

## Normal operation

```bash
# Show status
docker compose ps

# Show recent logs
docker compose logs --tail=100 rag-api

# Stop while preserving model and index caches
docker compose down

# Start again without rebuilding
docker compose up -d
```

Only use the following when you intentionally want to erase the downloaded model and retrieval-index caches:

```bash
docker compose down -v
```

## Connecting the experiment website

The browser frontend should call `http://localhost:8000/chat` during local development. Before deployment, set `ALLOWED_ORIGINS` in `.env` to the exact frontend origin, then restart:

```bash
docker compose up -d --force-recreate
```

Never place the Groq API key in frontend code. The key must remain in the backend `.env` file, which is excluded from the Docker image and ZIP.
