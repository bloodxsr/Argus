# AISOS Test Website

MERN stack scenario launcher for AISOS.

`index.html` is the Vite React entry point. `static-prototype.html` preserves the earlier standalone prototype.

## Services

- React/Vite client on `http://127.0.0.1:5173`
- Express API on `http://127.0.0.1:4100`
- MongoDB for replay session history
- Python Security AI API on `http://127.0.0.1:8000`

## Run

```bash
cp .env.example .env
npm install
npm run dev
```

Start the Python service first:

```bash
python -m uvicorn security_ai_service.api:app --host 127.0.0.1 --port 8000
```
