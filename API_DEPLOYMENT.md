# CiCC Pipeline API Deployment

This version runs the project as a web/API service instead of a Codex desktop conversation.

## Runtime model

1. User uploads manuscript files in the browser.
2. The API creates an isolated `jobs/JOB_ID/` folder.
3. The runner inspects the input files.
4. The converter calls the OpenAI Responses API with the CiCC rules and source manuscript.
5. The evaluator runs static checks and LaTeX compilation.
6. The API returns a downloadable output zip.

The user never accesses Codex directly. The server uses `CICC_LLM_API_KEY` from environment variables.

## Local run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and set CICC_LLM_API_KEY
uvicorn app.main:app --reload --port 8000
```

Open:

```text
http://localhost:8000
```

## Docker run

```bash
cp .env.example .env
# edit .env and set CICC_LLM_API_KEY
docker compose up --build
```

## API

Create a job:

```bash
curl -F "manuscript_id=CiCC-2026-42-1-R2" \
     -F "primary_source=tex" \
     -F "files=@input.zip" \
     http://localhost:8000/api/jobs
```

Check status:

```bash
curl http://localhost:8000/api/jobs/JOB_ID
```

Download:

```bash
curl -L -o output.zip http://localhost:8000/api/jobs/JOB_ID/download
```

## Server notes for IT

- Put the app behind Nginx/HTTPS.
- Keep `CICC_LLM_API_KEY` only on the server.
- Use Docker or another sandbox for LaTeX compilation.
- Uploaded TeX is compiled with `-no-shell-escape`.
- Each job is isolated in its own folder under `jobs/`.
- Add authentication before opening this to external users.
- Add scheduled cleanup for old `jobs/` folders.
