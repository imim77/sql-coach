# SQL Coach

A local practice desk for SQL. You get an exercise, write a query in the browser, run it against Postgres, and check the result. A wrong answer can ask for a hint. The hint does not include the query. The reference query stays on the server until you choose Show solution.

The practice data is Northline, a short-sea cargo ledger: ports, vessels, voyages, cargo, and crew.

## Run

Postgres is the only thing in Docker. The API and the page run on the host.

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

Open http://localhost:5173.

Set `OPENAI_API_KEY` in `backend/.env` if you want model-written notes. The key stays on the server. Hints use the OpenAI Responses API with `gpt-6-luna` unless you set `OPENAI_MODEL`. Without a key, Hint still works: each exercise has three saved notes. Create a key at https://platform.openai.com/api-keys.

## Reset the database

Init scripts run only when the volume is empty.

```bash
docker compose down -v
docker compose up -d
```

## Checks

```bash
cd backend && source .venv/bin/activate && pytest
```

Your query and the hidden reference query both run as the read-only `student` role. A match compares the result, so another wording of the same query can pass. Column names and column order are part of the answer. Row order matters only when the exercise says so.

The first ten exercises use the Northline tables. When you pass the last open exercise, the API writes another one in a new domain, creates its tables in Postgres, and adds it to the path. Later exercises stay locked until you pass the one before them. Generated lessons are saved in `backend/generated/`.
