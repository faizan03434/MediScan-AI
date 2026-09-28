# MediScan AI - Build and Deployment Guide

## Mobile App (Expo EAS Build)

### One-time setup
```
npm install -g eas-cli
eas login
cd apps/mobile
eas build:configure
```

### Build commands

Development APK (for testing on device):
```
eas build --platform android --profile development
```

Preview APK (internal testing):
```
eas build --platform android --profile preview
```

Production AAB (Google Play):
```
eas build --platform android --profile production
```

iOS builds (requires Apple Developer account):
```
eas build --platform ios --profile production
```

### Environment variables
Set in EAS dashboard: https://expo.dev/accounts/[username]/projects/mediscan-ai/secrets

Required:
- EXPO_PUBLIC_API_URL

### OTA Updates (no app store review needed)
```
eas update --branch production --message "Fix: scan result display"
```

---

## Backend (.NET API)

### Docker build
```
cd backend
docker build -t mediscan-api:latest .
docker run -p 5000:8080 --env-file .env mediscan-api:latest
```

### Azure App Service deploy
```
az webapp up --name mediscan-api --resource-group mediscan-rg --runtime "DOTNETCORE:9.0"
```

---

## AI Server (FastAPI)

### Docker build
```
cd ai-server
docker build -t mediscan-ai:latest .
docker run -p 8000:8000 -v ./models:/app/models mediscan-ai:latest
```

---

## Admin Dashboard (React + Vite)

### Build
```
cd apps/web-admin
npm install
npm run build
```
Output: apps/web-admin/dist/

### Deploy to Azure Static Web Apps
```
az staticwebapp create --name mediscan-admin --resource-group mediscan-rg
```

---

## Full stack with Docker Compose
```
docker-compose up -d
```
Services:
- API:       http://localhost:5000
- AI Server: http://localhost:8000
- Admin:     http://localhost:5173
- pgAdmin:   http://localhost:5050 (with --profile tools)
