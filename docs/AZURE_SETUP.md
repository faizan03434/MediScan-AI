# MediScan AI — Azure Free Tier Setup Guide

Azure free account gives you $200 credit for 30 days + always-free services.
Everything needed for MediScan AI development fits in the free tier.

---

## Step 1 — Create Azure Account

1. Go to https://azure.microsoft.com/free
2. Click **Start free** → Sign in with Microsoft/GitHub account
3. Enter credit card (for verification — NOT charged on free tier)
4. You get: **$200 credit (30 days)** + always-free services

---

## Step 2 — Azure OpenAI (GPT-4o)

> Free tier: $200 credit covers ~500,000 GPT-4o tokens

### Create the resource:
```
1. Portal → Search "Azure OpenAI" → Create
2. Region: East US (best model availability)
3. Pricing tier: Standard S0
4. Resource group: mediscan-rg
5. Name: mediscan-openai
```

### Deploy GPT-4o:
```
1. Go to resource → Azure OpenAI Studio → Deployments
2. Create new deployment:
   - Model: gpt-4o
   - Deployment name: gpt-4o     ← this goes in appsettings
   - Tokens per minute: 10K (free tier)
3. Click Deploy
```

### Get your keys:
```
Resource → Keys and Endpoint
- Endpoint: https://mediscan-openai.openai.azure.com/
- Key 1: <your-api-key>
```

---

## Step 3 — Azure Blob Storage

> Always free: 5 GB LRS storage

### Create storage account:
```
1. Portal → Search "Storage accounts" → Create
2. Resource group: mediscan-rg
3. Storage account name: mediscanstore (must be globally unique)
4. Region: East US
5. Performance: Standard
6. Redundancy: LRS (Locally redundant — cheapest)
7. Review + Create
```

### Get connection string:
```
Storage account → Access keys → Connection string (key1)
Looks like: DefaultEndpointsProtocol=https;AccountName=mediscanstore;...
```

### Create container:
```
Storage account → Containers → + Container
Name: mediscan-scans
Public access: Private (no anonymous access)
```

---

## Step 4 — Update appsettings.json

Edit `backend/MediScan.API/appsettings.json`:

```json
{
  "Azure": {
    "StorageConnectionString": "DefaultEndpointsProtocol=https;AccountName=mediscanstore;AccountKey=YOUR_KEY;EndpointSuffix=core.windows.net",
    "ContainerName": "mediscan-scans",
    "OpenAI": {
      "Endpoint": "https://mediscan-openai.openai.azure.com/",
      "ApiKey": "YOUR_AZURE_OPENAI_KEY",
      "DeploymentName": "gpt-4o",
      "ApiVersion": "2024-02-01"
    }
  }
}
```

---

## Step 5 — Verify Connection

Run the API and call the health endpoint:
```bash
cd backend
dotnet run --project MediScan.API
curl http://localhost:5000/api/v1/health
```

Test Azure OpenAI by scanning anything — the result should include
GPT-4o generated recommendations (not the fallback static text).

---

## Free Tier Limits

| Service | Free Allowance | MediScan Usage |
|---------|---------------|----------------|
| Azure OpenAI | $200 credit | ~500K tokens |
| Blob Storage | 5 GB LRS | ~5,000 scan images |
| App Service | F1 (60 CPU min/day) | Dev/staging only |
| PostgreSQL Flexible | Burstable B1ms | 32 GB storage |

---

## Cost Estimate (After Free Tier)

| Service | Monthly Cost |
|---------|-------------|
| Azure OpenAI GPT-4o | ~$5-15 (depends on scans) |
| Blob Storage 10GB | ~$0.20 |
| App Service B1 | ~$13 |
| PostgreSQL Flex B1ms | ~$12 |
| **Total** | **~$30-40/month** |

---

## Environment Variables (Never commit these!)

Add to `.env` (gitignored):
```
AZURE_OPENAI_ENDPOINT=https://mediscan-openai.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;...
AZURE_STORAGE_CONTAINER=mediscan-scans
```

---

## Troubleshooting

**"Azure OpenAI not configured" in logs**
→ Check `Azure:OpenAI:Endpoint` and `Azure:OpenAI:ApiKey` in appsettings.json

**"BlobServiceClient connection failed"**
→ Verify connection string format — must include AccountKey, not SAS token

**GPT-4o returns 429 (rate limit)**
→ Increase TPM limit in Azure OpenAI Studio → Deployments → Edit

**Storage container not found**
→ Run once: portal → create container named `mediscan-scans` with private access
