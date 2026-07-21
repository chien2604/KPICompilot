# AI KPI Copilot for Government PoC

PoC end-to-end gồm FastAPI backend, React/Vite/Ant Design frontend, PostgreSQL + pgvector, KùzuDB embedded, rule engine KPI, pipeline minh chứng và chatbot lãnh đạo.

## Backend setup

```bash
conda create -n kpi python=3.10 -y
conda activate kpi
cd backend
pip install -r requirements.txt
cp .env.example .env
docker compose up -d postgres
python -m db.init_db
python -m scripts.seed_from_excel_users
python main.py
```

Nếu không cấu hình `OPENAI_API_KEY`, hoặc LLM provider lỗi, backend tự dùng fallback mock/data-driven answer. Để dùng OpenRouter GPT-4o mini, đặt `OPENAI_MODEL=openai/gpt-4o-mini` và `OPENAI_BASE_URL=https://openrouter.ai/api/v1` trong `backend/.env`. Để dùng embedding thật bge-m3, đặt `USE_REAL_EMBEDDINGS=true`; mặc định PoC dùng mock embedding 1024 chiều để chạy nhanh.

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Mở:

- API docs: http://localhost:8001/docs
- Frontend: http://localhost:5173

Trong workspace hiện tại nếu port `8000` đang bận, chạy backend bằng:

```bash
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

và đặt frontend env:

```bash
VITE_API_BASE_URL=http://localhost:8001/api
```

## Luồng demo

1. Chọn demo user ở góc phải.
2. Mở Dashboard để xem KPI toàn Sở.
3. Mở Heatmap để xem phòng ban rủi ro.
4. Vào Công việc để tạo/xem nhiệm vụ.
5. Upload minh chứng ở màn Minh chứng.
6. Xem AI phân tích minh chứng.
7. Tính lại KPI bằng Rule Engine.
8. Hỏi AI Copilot bằng tiếng Việt.
9. Sinh báo cáo giao ban tự động.

## API chính

- `GET /api/kpi/dashboard?month=2026-06`
- `GET /api/kpi/heatmap?month=2026-06`
- `GET /api/tasks`
- `POST /api/evidences/upload`
- `POST /api/kpi/users/{user_id}/score/recompute`
- `POST /api/chatbot/message`
- `POST /api/reports/generate`

## Ghi chú PoC

- Không JWT, không Redis, không Celery/RQ, không MinIO.
- PostgreSQL lưu business data và vector chunks.
- KùzuDB lưu graph local tại `backend/storage/kuzu_db`.
- LLM chỉ giải thích/phân tích/trả lời/sinh báo cáo; điểm KPI do `KPIEngine` tính.
