# SupportLens

A lightweight observability platform for a customer support chatbot.

![alt text](screenshots/image.png)
![alt text](screenshots/image-1.png)
![alt text](screenshots/image-2.png)

## Features

- **AI-powered support chat** - Gemini 2.5 Flash with category classification
- **Trace analytics dashboard** - real-time KPIs and response-time tracking
- **Health monitoring** - `/health` endpoint with live status badge
- **Dockerised stack** - single `docker compose up` for the full stack

## Prerequisites

**Docker (recommended):** Docker

**Local development:** Python 3.14, Node.js 22, PostgreSQL

## Setup

### Run with Docker

```bash
git clone https://github.com/abdxdev/supportlens.git
cd supportlens
cp .env.example .env
```

> [!NOTE]
> Edit the `.env` file and add your Gemini API key:
>
> ```
> GEMINI_API_KEY=your_key_here
> ```
>
> Get a free key at [aistudio.google.com](https://aistudio.google.com/app/apikey).

```bash
docker compose up --build -d
```

Open **http://localhost** (port 80).

### Run locally without Docker

#### 1. Backend

```bash
git clone https://github.com/abdxdev/supportlens.git
cd supportlens/backend
cp .env.example .env
```

> [!NOTE]
> Edit `backend/.env` and set your Gemini API key and database credentials:
>
> ```
> GEMINI_API_KEY=your_key_here
> DATABASE_URL=postgresql://postgres:<password>@localhost:5432/postgres
> ```
>
> Get a free key at [aistudio.google.com](https://aistudio.google.com/app/apikey).

```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # macOS/Linux
python -m pip install -r requirements.txt
python seed_data.py
fastapi dev main.py
```

#### 2. Frontend (new terminal)

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Open **http://localhost:5173**.

## Health & Status

| Status        | Meaning                                                                                 |
| ------------- | --------------------------------------------------------------------------------------- |
| **Healthy**   | Database up, LLM configured                                                             |
| **Degraded**  | Database up, LLM unconfigured or failed to initialise - chat returns fallback responses |
| **Unhealthy** | Database unreachable - chat is disabled                                                 |

### Status screenshots

- Backend unreachable

  ![Backend unreachable](screenshots/image-3.png)

- LLM not configured

  ![LLM not configured](screenshots/image-4.png)

- Database unreachable

  ![Database unreachable](screenshots/image-5.png)

## CI / Testing

A GitHub Actions workflow (`.github/workflows/ci.yml`) runs on every push and PR to `main`:

1. **Lint** - ESLint (frontend) + Ruff (backend)
2. **E2E** - builds the full Docker stack and runs `scripts/e2e-test.sh`, which verifies:
   - Backend health endpoint
   - Seed data presence (≥ 25 traces)
   - Trace creation and analytics increment
   - Category filtering
   - Frontend reachability

Run the e2e tests locally:

```bash
docker compose up -d --build
bash scripts/e2e-test.sh
docker compose down -v
```
