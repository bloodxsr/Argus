#!/usr/bin/env sh
set -eu

if command -v docker >/dev/null 2>&1; then
  docker compose up --build
  exit 0
fi

echo "Docker is not installed. Start services manually:"
echo "1. Start MongoDB on mongodb://127.0.0.1:27017"
echo "2. Start NATS: nats-server -p 4222"
echo "3. uv run uvicorn ai.api:app --host 127.0.0.1 --port 9000"
echo "4. cd gateway && go run main.go"
echo "5. cd dashboard && npm install && npm run dev"
exit 1
