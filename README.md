# SQL Coach

A local practice desk for SQL. You write a query in the browser, run it against Postgres, and check the result. The practice data is Northline: ports, vessels, voyages, cargo, and crew.

## Run in one container

Install Docker. This image includes the page, the API, and the Northline database.

```bash
docker build -t sql-coach .
docker run --rm -p 8000:8000 sql-coach
```

Open http://localhost:8000.

If port 8000 is already in use, pick another host port: `-p 18080:8000`, then open http://localhost:18080.

The database is created the first time the container starts. Keep it across restarts with a volume:

```bash
docker run --rm -p 8000:8000 -v sqlcoach-pg:/var/lib/postgresql/data sql-coach
```

Load Northline again by removing that volume and starting a new container:

```bash
docker volume rm sqlcoach-pg
```

Built-in exercises are in the image. A task you add, or a lesson the coach generates, stays in that container until you remove it.

For model-written notes, pass the key when you start the container. Each exercise also has three saved notes, so Hint works without a key. The model is `gpt-6-luna` unless you set `OPENAI_MODEL`.

```bash
docker run --rm -p 8000:8000 -e OPENAI_API_KEY=sk-... sql-coach
```

Create a key at https://platform.openai.com/api-keys. The key stays in the container.

## Run on the host

Use this while changing the API or the page. Postgres runs in Docker. The API and the page run on your machine. You need Python 3 and Node.js.

```bash
docker compose up -d
```

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The page sends `/api` to the API on port 8000.

Put `OPENAI_API_KEY` in `backend/.env` for model-written notes. `backend/.env.example` has the database URLs the API expects.

Init scripts run when the Compose volume is empty. Load the practice data again with:

```bash
docker compose down -v
docker compose up -d
```

## Checks

From `backend`, with the virtualenv active:

```bash
pytest
```
