# ── Build stage ──────────────────────────────────────────────
FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
WORKDIR /src

# Copy solution and project files first (layer caching)
COPY MediScan.sln .
COPY MediScan.API/MediScan.API.csproj         MediScan.API/
COPY MediScan.Core/MediScan.Core.csproj       MediScan.Core/
COPY MediScan.Infra/MediScan.Infra.csproj     MediScan.Infra/
COPY MediScan.Tests/MediScan.Tests.csproj     MediScan.Tests/

# Restore packages
RUN dotnet restore MediScan.sln

# Copy all source files
COPY . .

# Build & publish
RUN dotnet publish MediScan.API/MediScan.API.csproj \
    -c Release -o /app/publish --no-restore

# ── Runtime stage ─────────────────────────────────────────────
FROM mcr.microsoft.com/dotnet/aspnet:9.0 AS runtime
WORKDIR /app

# Security: run as non-root
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && adduser --disabled-password --gecos "" appuser
COPY --from=build /app/publish .
RUN mkdir -p /app/.auth /app/wwwroot/uploads \
    && chown -R appuser:appuser /app/.auth /app/wwwroot
USER appuser

EXPOSE 8080
ENTRYPOINT ["dotnet", "MediScan.API.dll"]
