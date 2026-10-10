# MediScan AI 🏥

> **Current status (4 October 2026): research development preview.** The original feature/compliance list below describes intended capabilities, not implemented or validated medical performance. Printed-English offline OCR, editable confirmation, exact medicine reference lookup and owner-scoped account activity are implemented. Skin intake contains 1,864 distinct decoded images across two sources; the six-class CNN scored 35.5% internal held-out balanced accuracy. MobileNet transfer training completed with 37.4% validation balanced accuracy and no new test evaluation. Additional anemia, fingernail and wound mirrors are [downloaded and audited](docs/MEDICAL_DATA_INTAKE.md), with data/rights issues retained in quarantine. See the [current implementation status](docs/IMPLEMENTATION_STATUS.md). Clinical inference, live medical ROI detection, Pakistan registration lookup and compliance work remain pending. Current captures deliberately return inconclusive. Use synthetic data only.
>
> Start with the [implementation audit and strategy](docs/PRODUCT_STRATEGY.md) and [iPhone QR preview guide](docs/IPHONE_PREVIEW.md). Actual local stack: .NET 9 API on port 5000, internal preview AI on 8001, Expo SDK 54 on 8081. Run `dotnet build backend/MediScan.sln`, then `./infrastructure/Start-Preview.ps1` after dependencies are installed.

A HIPAA-aware, AI-powered mobile health assistant that uses live camera for real-time medical detection, tracks health history, and gives actionable lifestyle + medication guidance.

---

## 🌟 Features

| Module | Description |
|--------|-------------|
| 🩸 Anemia Detection | Live camera scans eye/nail pallor to detect anemia |
| 🦠 Skin Disease Detection | Detects Eczema, Fungal, Acne types via camera |
| 🦴 Posture & Scoliosis | Backbone curve analysis using MediaPipe Pose |
| 👁️ Eye Disease Detection | Cataract, Jaundice, Red Eye early detection |
| 🩹 Wound Measurement | Wound size (cm) + healing stage from photo |
| 👅 Tongue Diagnosis | Color-based deficiency & infection detection |
| 💊 Medication Scanner | Barcode + OCR prescription scanner with drug info |
| 📊 Health Dashboard | Full scan history, trends, reminders |

---

## 🏗️ Architecture

```
React Native (Expo) App
        │
  .NET 8 Web API (Gateway + Auth)
        │
   ┌────┴────┐
FastAPI    Azure OpenAI
AI Server  (Recommendations)
        │
PostgreSQL + Redis + Azure Blob
```

---

## 📁 Project Structure

```
mediscan-ai/
├── apps/
│   ├── mobile/          # React Native (Expo) — iOS & Android
│   └── web-admin/       # React Web Admin Dashboard
├── backend/
│   ├── MediScan.API/    # .NET 8 Web API
│   ├── MediScan.Core/   # Business Logic, Entities, DTOs
│   ├── MediScan.Infra/  # DB, Storage, External APIs
│   └── MediScan.Tests/  # Unit + Integration Tests
├── ai-server/           # FastAPI AI Inference Server
│   ├── models/          # Trained model files (.pt, .onnx)
│   ├── routers/         # Per-module API routes
│   ├── training/        # Model training scripts
│   └── utils/           # Preprocessing helpers
├── docs/                # Architecture docs, API specs
├── infrastructure/      # Docker, Azure IaC
└── .github/workflows/   # CI/CD pipelines
```

---

## 🚀 Quick Start (Local Dev)

### Prerequisites
- Docker Desktop
- .NET 8 SDK
- Node.js 20+
- Python 3.11+
- Expo CLI (`npm install -g expo-cli`)

### 1. Clone the repo
```bash
git clone https://github.com/faizan03434/MediScan-AI.git
cd MediScan-AI
```

### 2. Start infrastructure (DB + Redis)
```bash
docker-compose up -d postgres redis
```

### 3. Start .NET API
```bash
cd backend/MediScan.API
dotnet run
# Runs on http://localhost:5000
```

### 4. Start AI Server
```bash
cd ai-server
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# Runs on http://localhost:8000
```

### 5. Start Mobile App
```bash
cd apps/mobile
npm install
npx expo start
```

---

## 🔐 HIPAA Compliance

- AES-256 encryption at rest
- TLS 1.3 in transit
- Full audit logging (who, when, what)
- Role-based access control (User, Doctor, Admin)
- Consent management before every scan
- Data retention policy with user control
- No PII in logs
- 2FA for Doctor accounts

---

## 🤖 AI Models

| Detection | Architecture | Dataset |
|-----------|-------------|---------|
| Anemia | YOLOv8 + EfficientNet-B4 | Kaggle Anemia Eye Pallor |
| Skin Disease | YOLOv8 + EfficientNet-B3 | HAM10000 |
| Posture | MediaPipe Pose + YOLOv8-Pose | Public Pose Datasets |
| Eye Disease | YOLOv8-Seg + Color CNN | Kaggle Eye Datasets |
| Wound | YOLOv8-Seg + OpenCV | Wound Dataset |
| Tongue | YOLOv8 + MobileNetV3 | Custom Curated |

---

## 🌐 External APIs

- **OpenFDA** — Drug information
- **Pakistan DAP** — Local drug registry
- **Azure OpenAI (GPT-4o)** — AI recommendations & advice
- **Local OCR** — Windows offline English OCR; optional EasyOCR for other hosts (see docs/OCR_AND_PRESCRIPTION.md)

---

## 📅 Development Phases

- **Phase 1** — Foundation (Auth, DB, API scaffold)
- **Phase 2** — Core AI Models (Train + Integrate all 6)
- **Phase 3** — Live Camera Integration
- **Phase 4** — Medication Scanner Module
- **Phase 5** — Polish, HIPAA Audit, Testing

---

## ⚠️ Disclaimer

MediScan AI is an **assistive tool** and does **not replace professional medical advice**. Always consult a licensed doctor before making any health decisions. All medication recommendations are informational only.

---

## 👨‍💻 Developer

Built with ❤️ by Faizan — AI/ML Engineer | .NET Developer | React Developer | Full Stack
