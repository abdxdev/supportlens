# SupportLens

A lightweight observability platform for a customer support chatbot. Built with **FastAPI**, **Gemini AI**, **SQLite**, and **React + shadcn/ui**.

## Features

- **Support Chatbot** — Live chat powered by Gemini (`gemini-2.0-flash`) acting as a SaaS billing support agent.
- **Auto-classification** — Every conversation is classified into one of 5 categories by a second Gemini call using structured JSON output.
- **Observability Dashboard** — Aggregate stats (total traces, category breakdown, avg response time), a bar chart, and a filterable/expandable trace table.
- **25 seed traces** pre-loaded for a realistic starting state.

## Quick Start (single command after setup)

### 1. Prerequisites

| Tool    | Version |
| ------- | ------- |
| Python  | 3.11+   |
| Node.js | 18+     |
| npm     | 9+      |

### 2. Clone & configure

```bash
git clone <your-repo-url>
cd supportlens
```

Copy the env file and add your Gemini API key:

```bash
cp backend/.env.example backend/.env
# Edit backend/.env and set GEMINI_API_KEY=your_key_here
```

Get a free Gemini API key at [aistudio.google.com](https://aistudio.google.com/app/apikey).

### 3. Run everything

**Windows (PowerShell):**

```powershell
.\start.ps1
```

**macOS / Linux:**

```bash
bash start.sh
```

This single command will:

1. Create a Python virtual environment in `backend/.venv`
2. Install all backend dependencies
3. Seed the database with 25 pre-classified traces
4. Start the FastAPI backend on **http://localhost:8000**
5. Install frontend npm packages (first run only)
6. Start the Vite dev server on **http://localhost:5173**

Open **http://localhost:5173** in your browser.

## Manual setup (alternative)

```bash
# Backend
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
python seed_data.py
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

## API Reference

| Method | Endpoint                   | Description                           |
| ------ | -------------------------- | ------------------------------------- |
| `POST` | `/chat`                    | Generate a chatbot reply              |
| `POST` | `/traces`                  | Classify & save a trace               |
| `GET`  | `/traces?category=Billing` | List traces, optional category filter |
| `GET`  | `/analytics`               | Aggregate stats                       |

## Classification Categories

| Category            | Description                                   |
| ------------------- | --------------------------------------------- |
| **Billing**         | Invoices, charges, payment methods, pricing   |
| **Refund**          | Refund requests, disputes, credits            |
| **Account Access**  | Login issues, password reset, MFA             |
| **Cancellation**    | Cancel subscription, downgrade, close account |
| **General Inquiry** | Feature questions, how-to, product info       |

Classification is performed by Gemini using a structured-output prompt with `response_mime_type: application/json` and an enum schema — no keyword matching or regex.
