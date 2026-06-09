#!/usr/bin/env sh
set -eu

if command -v docker >/dev/null 2>&1; then
  docker compose up --build
  exit 0
fi

echo "Docker is not installed. Start services manually:"
echo "1. Start MongoDB on mongodb://127.0.0.1:27017"
echo "2. python -m uvicorn security_ai_service.api:app --host 127.0.0.1 --port 8000"
echo "3. cd test-website && npm install && npm run dev"
echo "4. cd report-website && npm install && npm run dev"
exit 1
