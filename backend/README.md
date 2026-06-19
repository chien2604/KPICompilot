# Backend - AI KPI Copilot

FastAPI backend cho PoC AI KPI Copilot for Government.

```bash
conda activate kpi
pip install -r requirements.txt
docker compose up -d postgres
python -m db.init_db
python scripts/seed_from_excel.py
python scripts/seed_demo_data.py
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

Port `8001` đang được dùng trong workspace này vì `8000` đã bận. PostgreSQL pgvector chạy ở host port `5433`.

Backend tự dùng `MockLLMClient` nếu `OPENAI_API_KEY` trống hoặc LLM provider lỗi. Không cần JWT, Redis, Celery/RQ, Neo4j hay MinIO.

Để dùng OpenRouter, cấu hình trong `backend/.env`:

```bash
OPENAI_API_KEY=your_openrouter_key
OPENAI_MODEL=openai/gpt-4o-mini
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_SITE_URL=http://localhost:5173
OPENROUTER_APP_NAME=AI KPI Copilot for Government
```
