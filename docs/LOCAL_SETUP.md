# MediScan AI — Local Development Setup

## Prerequisites

| Tool | Version | Download |
|------|---------|----------|
| .NET SDK | 9.0+ | https://dotnet.microsoft.com/download |
| Python | 3.11+ | https://python.org/downloads |
| Node.js | 20+ | https://nodejs.org |
| Docker Desktop | Latest | https://docker.com/products/docker-desktop |
| Git | Latest | https://git-scm.com |

---

## Step 1 — Start Database + Redis (Docker)

```bash
# Only Postgres + Redis (no Docker needed for API/AI)
docker-compose -f docker-compose.dev.yml up -d

# Verify they're running
docker ps
```

If Docker is not installed yet:
- Download Docker Desktop: https://www.docker.com/products/docker-desktop
- Install and restart your machine
- Run the command above

---

## Step 2 — .NET API

```bash
cd backend

# Copy environment file
copy ..\env.example .env  # (edit values)

# Run database migrations
dotnet ef database update --project MediScan.Infra --startup-project MediScan.API

# Start API
dotnet run --project MediScan.API
# Runs on: http://localhost:5000
# Swagger:  http://localhost:5000/swagger
```

---

## Step 3 — FastAPI AI Server

```bash
cd ai-server

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # Mac/Linux

# Install CPU-only PyTorch first (smaller download)
pip install torch==2.4.1+cpu torchvision==0.19.1+cpu --index-url https://download.pytorch.org/whl/cpu

# Install all other dependencies
pip install -r requirements.txt

# Copy env file
copy .env.example .env

# Start server
uvicorn main:app --reload --port 8000
# Runs on: http://localhost:8000
# Docs:    http://localhost:8000/docs
```

---

## Step 4 — React Native Mobile App

```bash
cd apps/mobile

# Install dependencies
npm install --legacy-peer-deps

# Copy env file
copy ..\..\env.example .env

# Start Expo
npx expo start

# Then press:
# a — Android emulator
# i — iOS simulator (Mac only)
# w — Web browser
# Scan QR code with Expo Go app on your phone
```

---

## Environment Variables

Copy `.env.example` to `.env` in the root and fill in:

```
# Required for local dev (minimum):
POSTGRES_PASSWORD=mediscan_pass
JWT_SECRET=any-string-min-32-characters-here
AZURE_OPENAI_API_KEY=         # Optional — GPT-4o recommendations
AZURE_STORAGE_CONNECTION_STRING=  # Optional — image storage
```

Azure Storage is optional for local dev — images won't be stored but scans still work.

---

## Full Docker Stack (Optional)

If you want everything in Docker:

```bash
docker-compose up -d
# API:       http://localhost:5000
# AI Server: http://localhost:8000
# pgAdmin:   http://localhost:5050 (with --profile tools)
```

---

## Model Files

AI models are NOT included in the repo (too large for GitHub).

For development, routers use **color/geometric analysis fallbacks** automatically when `.pt` files are missing — so you can test all endpoints without trained models.

To train models:
```bash
cd ai-server
python training/train_anemia.py --data_dir ./datasets/anemia
python training/train_skin.py   --data_dir ./datasets/ham10000
```

See `docs/TRAINING_GUIDE.md` for dataset download instructions.
