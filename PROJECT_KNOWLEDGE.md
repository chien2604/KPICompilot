# PROJECT KNOWLEDGE - AI KPI Copilot for Government

Tài liệu này mô tả dự án theo source code thực tế tại thời điểm đọc. Mục tiêu là giúp AI Agent, lập trình viên mới, Tech Lead và Product Owner hiểu nhanh hệ thống mà không cần mở toàn bộ source từ đầu.

## 1. Tổng Quan Dự Án

### Mục Tiêu Hệ Thống

AI KPI Copilot for Government là bản PoC cho bài toán theo dõi KPI, nhiệm vụ, minh chứng và hỗ trợ lãnh đạo ra quyết định trong một đơn vị cấp Sở. Hệ thống mô phỏng khoảng 38 cán bộ thuộc nhiều phòng ban, có nhiệm vụ được giao, file minh chứng, điểm KPI và báo cáo giao ban.

Đối tượng sử dụng chính:

- Lãnh đạo Sở: xem dashboard, heatmap, hỏi chatbot, sinh báo cáo.
- Trưởng/phó phòng: theo dõi cán bộ, tiến độ nhiệm vụ, minh chứng.
- Cán bộ/chuyên viên: upload minh chứng và theo dõi nhiệm vụ được giao.
- Tech/Product team: demo end-to-end flow KPI + AI + RAG.

Giá trị mang lại:

- Gom dữ liệu KPI, nhiệm vụ, minh chứng vào một luồng demo thống nhất.
- Cho thấy Rule Engine tính KPI, LLM chỉ giải thích/phân tích/chuyển dữ liệu thành ngôn ngữ lãnh đạo.
- Có nền tảng RAG gồm vector chunks trong PostgreSQL/pgvector và graph context trong KùzuDB embedded.

### Chức Năng Chính

- Dashboard KPI toàn Sở.
- Heatmap KPI theo phòng ban.
- Hồ sơ cán bộ và điểm KPI.
- Quản lý nhiệm vụ, giao nhiệm vụ cho cán bộ.
- Upload và phân tích minh chứng.
- KPI Rule Engine và AI giải thích KPI.
- AI Copilot Chat cho câu hỏi tiếng Việt.
- Sinh báo cáo giao ban HTML/text đơn giản.
- Seed dữ liệu demo gồm phòng ban, users, tasks, evidences, chunks, KPI scores, reports, chat logs.

## 2. Kiến Trúc Tổng Thể

### Sơ Đồ Hệ Thống

```text
React/Vite/Ant Design Frontend
        |
        | Axios REST API
        v
FastAPI Backend
        |
        | routes -> services -> db models
        v
PostgreSQL + pgvector
        |
        | business data + document_chunks vector(1024)
        v
Local storage uploads
        |
        | evidence file extraction + chunking + embedding
        v
KùzuDB embedded graph store
```

Luồng AI/RAG:

```text
Frontend
  -> Backend API
  -> Business Service
  -> LLM Client
  -> GraphRAGService
  -> PGVectorStore + KuzuGraphStore
  -> PostgreSQL + local KùzuDB
```

### Công Nghệ Sử Dụng

Backend:

| Thành phần | Công nghệ |
| --- | --- |
| API framework | FastAPI |
| Server | Uvicorn |
| ORM | SQLAlchemy 2.x |
| Schema validation | Pydantic |
| Config | pydantic-settings, dotenv |
| Database | PostgreSQL |
| Vector DB | pgvector extension |
| Graph DB embedded | KùzuDB |
| File extraction | Docling fallback, pypdf, python-docx, pandas/openpyxl tùy module |
| LLM client | OpenAI-compatible SDK, Groq-compatible, MockLLM |
| Embedding | MockEmbedding hoặc BAAI/bge-m3 qua sentence-transformers |

Frontend:

| Thành phần | Công nghệ |
| --- | --- |
| App framework | React 18 |
| Build tool | Vite |
| UI | Ant Design |
| Charts | Recharts |
| HTTP | Axios |
| Routing | react-router-dom |

Database:

| Thành phần | Công nghệ |
| --- | --- |
| Business data | PostgreSQL |
| Vector chunks | pgvector `vector(1024)` |
| Graph knowledge base | KùzuDB embedded local path |
| File storage | Local filesystem `backend/storage/uploads` |

AI:

| Thành phần | Công nghệ |
| --- | --- |
| LLM | OpenAI-compatible client, Groq-compatible client, MockLLM fallback |
| KPI explanation | Prompt file + LLM |
| Evidence analysis | Two-phase prompt trong code |
| Report generation | Prompt file + LLM |
| RAG | pgvector + KùzuDB |

## 3. Cấu Trúc Thư Mục Toàn Dự Án

```text
AI_for_kpi_goverment/
├── backend/
│   ├── ai_layer/
│   ├── api/
│   ├── core/
│   ├── db/
│   ├── schemas/
│   ├── scripts/
│   ├── services/
│   ├── storage/
│   ├── docker-compose.yml
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── layouts/
│   │   ├── pages/
│   │   ├── styles/
│   │   └── utils/
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── *.xlsx
├── *.docx
├── *.pdf
├── README.md
└── PROJECT_KNOWLEDGE.md
```

Nhiệm vụ từng vùng:

- `backend/`: toàn bộ API, business logic, AI layer, RAG, database models, seed scripts.
- `frontend/`: React UI cho 9 màn hình demo, API client, shared components.
- File Excel ở root: nguồn rule KPI theo vai trò. Trong code hiện tại loader chỉ kiểm tra/touch file và seed template từ spec hardcode.
- `backend/storage/uploads/`: file minh chứng local và file seed demo.
- `backend/storage/kuzu_db/`: dữ liệu KùzuDB local nếu Kùzu khả dụng.

## 4. Phân Tích Backend

### Cấu Trúc Backend

```text
backend/
├── main.py
├── api/routes/
├── core/
├── db/
│   ├── database.py
│   ├── init_db.py
│   └── models/
├── schemas/
├── services/
├── ai_layer/
│   ├── prompts/
│   └── rag/
├── scripts/
├── storage/
├── requirements.txt
└── docker-compose.yml
```

### Vai Trò Các Thư Mục Backend

| Thư mục | Vai trò | Quan hệ |
| --- | --- | --- |
| `api/routes` | Định nghĩa REST endpoint FastAPI | Gọi service hoặc query DB trực tiếp |
| `services` | Business logic: nhiệm vụ, minh chứng, KPI, chatbot, báo cáo | Được routes gọi; gọi model, AI layer, RAG |
| `db/models` | SQLAlchemy ORM model cho PostgreSQL | Được routes/services/scripts dùng |
| `schemas` | Pydantic input/output schema | Được routes dùng cho request body |
| `core` | Config và logging | Được toàn backend dùng |
| `ai_layer` | LLM, prompt, analyzer, explainer, report generator | Được services gọi |
| `ai_layer/rag` | Document loader, chunker, embedding, pgvector, Kùzu, GraphRAG | Được EvidenceService/ChatbotService gọi |
| `scripts` | Seed DB và smoke test | Chạy thủ công khi setup/demo |

## 5. Phân Tích Chi Tiết Backend

### Entry, Core Và Database

| File | Mục đích | Ai gọi file này | File này gọi ai | Nếu xoá file này mất gì |
| --- | --- | --- | --- | --- |
| `backend/main.py` | Khởi tạo FastAPI app, CORS, mount routers, health check, chạy Uvicorn port 8001 | `python main.py`, Uvicorn | `api.routes.*`, `core.config`, `core.logging` | Backend API không chạy |
| `backend/core/config.py` | Đọc `.env`, định nghĩa settings như DB URL, LLM key, CORS, storage paths | Gần như toàn backend | `pydantic_settings`, filesystem | App mất cấu hình trung tâm |
| `backend/core/logging.py` | Cấu hình logging basic | `main.py` | Python logging | Log mặc định kém nhất quán |
| `backend/db/database.py` | Tạo engine, session, dependency `get_db`, bật pgvector extension | Routes, services, scripts, init_db | SQLAlchemy, settings | Không truy cập DB được |
| `backend/db/init_db.py` | Tạo extension pgvector và tạo bảng ORM | CLI setup | `db.models`, `Base.metadata` | Không init schema DB được |
| `backend/core/__init__.py`, `backend/db/__init__.py`, `backend/api/__init__.py` | Package marker | Python import system | Không gọi logic | Có thể ảnh hưởng import package nếu xoá |

### API Routes

| File | Trách nhiệm | Hàm chính | Phụ thuộc | Nếu xoá |
| --- | --- | --- | --- | --- |
| `api/routes/users.py` | List/get cán bộ, list theo phòng | `list_users`, `get_user`, `list_by_department` | `User`, `Department`, `get_db` | FE selector cán bộ và hồ sơ mất dữ liệu user |
| `api/routes/departments.py` | List phòng ban, users trong phòng | `list_departments`, `department_users` | `Department`, `User` | Header/task grouping theo phòng ban hỏng |
| `api/routes/tasks.py` | CRUD nhiệm vụ, filter theo status/department/assigned_user/month, stats | `list_tasks`, `create_task`, `update_task`, `delete_task`, `update_status`, `task_stats` | `TaskService`, `Task`, `TaskAssignment` | Quản lý nhiệm vụ và evidence task select hỏng |
| `api/routes/evidences.py` | Upload, list/filter, get, analyze evidence | `upload_evidence`, `list_evidences`, `analyze_evidence`, `get_analysis`, `get_evidence` | `EvidenceService`, `TaskEvidence` | Upload/phân tích minh chứng hỏng |
| `api/routes/kpi.py` | Dashboard, heatmap, profile, score, recompute, criteria, ranking | `dashboard`, `heatmap`, `user_profile`, `user_score`, `recompute`, `criteria`, `ranking` | `KPIEngine`, KPI models | Dashboard, heatmap, hồ sơ, AI đánh giá hỏng |
| `api/routes/chatbot.py` | Endpoint chatbot leadership copilot | `chatbot_message` | `ChatbotService`, `ChatbotMessageIn` | AI Copilot Chat hỏng |
| `api/routes/reports.py` | Generate/list/get reports | `generate_report`, `list_reports`, `get_report` | `ReportService`, `Report` | Báo cáo tự động hỏng |
| `api/routes/__init__.py` | Package marker | Không có logic | Python import | Có thể ảnh hưởng import package |

Luồng route điển hình:

1. FE gọi `/api/...`.
2. Route nhận query/body qua FastAPI/Pydantic.
3. Route lấy DB session từ `get_db`.
4. Route query trực tiếp hoặc gọi service.
5. Service xử lý business/AI/RAG.
6. Route trả dict/list dict cho FE.

### Services

#### `services/task_service.py`

Mục đích: tạo và cập nhật nhiệm vụ, đồng thời tạo dòng `task_assignments` cho danh sách cán bộ được giao.

Hàm chính:

| Hàm | Vai trò |
| --- | --- |
| `create(payload)` | Tạo `Task`, flush lấy id, tạo `TaskAssignment` cho từng `assigned_user_ids`, commit |
| `update(task, payload)` | Cập nhật field task và nếu có `progress_percent` thì cập nhật mọi assignment của task |

Phụ thuộc: `Task`, `TaskAssignment`, `TaskCreate`, `TaskUpdate`, SQLAlchemy Session.

Nếu xoá: API tạo/sửa nhiệm vụ mất business logic, route task không còn hoạt động đúng.

#### `services/evidence_service.py`

Mục đích: xử lý upload minh chứng end-to-end.

Luồng `upload_and_process`:

1. Lưu file local bằng `FileStorage`.
2. Tạo `TaskEvidence` status `PROCESSING`.
3. Gọi `GraphRAGService.index_evidence`.
4. Lấy task/user/deadline để build context.
5. Gọi `EvidenceAnalyzer.analyze`.
6. Lưu `ai_relevance_score`, `ai_summary`, checklist/strength/weakness dưới JSON string trong `ai_missing_points`.
7. Set status `ANALYZED`.
8. Nếu lỗi, rollback và tạo evidence mới status `FAILED`.

Hàm `analyze(evidence_id)` chạy lại AI analysis dựa trên `extracted_text` đã lưu.

Phụ thuộc: `FileStorage`, `GraphRAGService`, `EvidenceAnalyzer`, `TaskEvidence`, `Task`, `User`.

Nếu xoá: upload minh chứng không còn pipeline AI/RAG.

Chưa hoàn thiện:

- Có `traceback.print_exc()` trong exception boundary, chưa sạch theo chuẩn production.
- Khi lỗi upload, transaction rollback rồi tạo evidence mới; có thể mất id ban đầu.
- Chưa kiểm tra quyền user có thật sự được giao task trước khi upload.

#### `services/kpi_engine.py`

Mục đích: tính điểm KPI bằng rule engine, không để LLM tính điểm.

Hàm chính:

| Hàm | Vai trò |
| --- | --- |
| `compute_user_score(user_id, period_month)` | Tính điểm theo user/template/criteria/tasks/evidence |
| `recompute_and_save(user_id, period_month)` | Tính lại, gọi AI explainer, upsert `kpi_scores` |
| `classify(score)` | Mapping điểm sang xếp loại |
| `risk_level(score)` | LOW/MEDIUM/HIGH theo score |
| `_task_assignment_score(assignment)` | Tính score từng nhiệm vụ từ status, progress/self/leader score, evidence relevance, document type |
| `_group_breakdown(criteria, avg_task_score, overdue_count, role)` | Phân bổ điểm theo nhóm tiêu chí |

Công thức nhiệm vụ hiện tại:

```text
score = 100 * (
  0.45 * status_factor
  + 0.25 * progress/self/leader factor
  + 0.20 * evidence_factor
  + 0.10 * document_type_factor
)
```

Phân loại:

- `>= 90`: Hoàn thành xuất sắc nhiệm vụ.
- `>= 80`: Hoàn thành tốt nhiệm vụ.
- `>= 65`: Hoàn thành nhiệm vụ.
- `< 65`: Không hoàn thành nhiệm vụ.

Risk:

- `>= 85`: LOW.
- `>= 70`: MEDIUM.
- `< 70`: HIGH.

Phụ thuộc: KPI models, Task/Assignment/Evidence/User, `KPIExplainer`.

Nếu xoá: KPI score/recompute/dashboard chi tiết mất rule chính.

Chưa hoàn thiện:

- Công thức là heuristic PoC, chưa phản ánh đầy đủ rule Excel chi tiết.
- Period month chưa filter task theo period trong `compute_user_score`; hiện lấy toàn bộ assignment của user.

#### `services/chatbot_service.py`

Mục đích: chatbot lãnh đạo bằng tiếng Việt.

Luồng:

1. `detect_intent(message)` bằng keyword tiếng Việt.
2. `_structured_data(intent, month, department_id)` query PostgreSQL cho dữ liệu phù hợp.
3. `GraphRAGService.build_chat_context` lấy vector context và graph context.
4. Build prompt tiếng Việt.
5. Gọi LLM qua `get_llm_client`.
6. Nếu lỗi, fallback answer theo intent.
7. Lưu `ChatLog`.

Intent hỗ trợ theo code:

- `KPI_RISK_USERS`
- `SLOW_DEPARTMENTS`
- `EMPLOYEE_PROFILE`
- `TASK_STATUS`
- `EVIDENCE_EXPLAIN`
- `GENERATE_REPORT`
- `GENERAL_HELP`

Phụ thuộc: `get_llm_client`, `GraphRAGService`, `ChatLog`, `User`, `Department`, `KPIScore`, `Task`.

Nếu xoá: `/api/chatbot/message` không trả lời được.

Chưa hoàn thiện:

- Intent detection chỉ dựa keyword, chưa dùng model/classifier.
- Với nhiều intent, `_structured_data` chỉ trả task status chung.
- `user_id` hiện không được truyền vào GraphRAG context trong `answer`; chỉ dùng để log.
- Prompt file `chatbot_copilot_prompt.txt` tồn tại nhưng service hiện build prompt inline, chưa đọc prompt file.

#### `services/report_service.py`

Mục đích: gom dữ liệu DB và gọi AI sinh báo cáo giao ban.

Luồng:

1. `_collect_data(period, department_id)` đếm users/tasks, task status, risk users.
2. `ReportGenerator.generate(data)` sinh HTML.
3. Lưu `Report`.

Phụ thuộc: `ReportGenerator`, `Report`, `Task`, `User`, `Department`, `KPIScore`.

Nếu xoá: chức năng sinh báo cáo không hoạt động.

Chưa hoàn thiện:

- `tasks_by_status` hiện không áp dụng `department_id` dù `task_query` có filter riêng; report theo phòng có thể vẫn dùng status toàn Sở.
- Không export PDF/DOCX, chỉ HTML/text.

#### `services/excel_rule_loader.py`

Mục đích: seed KPI template, criteria group và document type rules.

Thực tế source:

- `ROLE_TEMPLATES` và `DOCUMENT_RULES` được hardcode trong Python.
- `_touch_excel_files()` chỉ mở thử các file Excel nếu tồn tại, không parse chi tiết cell thành rule.
- `seed()` xoá criteria/score/template/document rules rồi tạo lại.

Phụ thuộc: `openpyxl`, KPI models.

Nếu xoá: không seed được rule KPI/doc type rule.

Chưa hoàn thiện:

- Chưa parse rule chi tiết từ Excel.
- Có dòng delete template lặp 2 lần.
- Có `pass` khi lỗi mở Excel, lỗi bị nuốt.

#### `services/file_storage.py`

Mục đích: lưu file upload vào local storage với uuid prefix.

Phụ thuộc: `UploadFile`, settings upload dir.

Nếu xoá: upload minh chứng không lưu file.

#### `services/extractor.py`

Mục đích: module trích xuất file PDF/Word/Excel/Image bằng nhiều thư viện. Trả `ExtractionResult` gồm text, image_b64, page_count, is_image, error.

Phụ thuộc: `pdfplumber`, `pypdf`, `python-docx`, `openpyxl`, `PIL` nếu cài.

Quan hệ thực tế: file tồn tại nhưng pipeline hiện tại của `EvidenceService` dùng `ai_layer/rag/document_loader.py`, không dùng trực tiếp `services/extractor.py`.

Nếu xoá: chưa ảnh hưởng luồng upload hiện tại, nhưng mất utility extractor mở rộng.

Chưa hoàn thiện:

- Có nhiều fallback runtime import.
- Chưa được route/service chính gọi.

#### `services/__init__.py`

Package marker, không có logic. Xoá có thể ảnh hưởng import package tùy môi trường.

### AI Layer

| File | Mục đích | Ai gọi | Gọi ai | Nếu xoá |
| --- | --- | --- | --- | --- |
| `ai_layer/llm_client.py` | Abstraction LLM: Base, Mock, OpenAI, Groq, factory | Analyzer, Explainer, Report, Chatbot | OpenAI SDK, settings | Toàn bộ AI text generation mất client |
| `ai_layer/evidence_analyzer.py` | Two-phase evidence analysis: sinh checklist từ task, đối chiếu với evidence text | `EvidenceService` | LLM client | AI phân tích minh chứng mất |
| `ai_layer/kpi_explainer.py` | Đọc prompt KPI explainer và gọi LLM giải thích score đã tính | `KPIEngine` | LLM client, prompt file | KPI vẫn tính được nhưng mất giải thích AI |
| `ai_layer/report_generator.py` | Đọc prompt report và gọi LLM sinh HTML report | `ReportService` | LLM client, prompt file | Báo cáo AI mất nội dung sinh tự động |
| `ai_layer/__init__.py` | Package marker | Import system | Không | Ảnh hưởng package import nếu xoá |

#### `ai_layer/llm_client.py`

Luồng chọn client:

1. Nếu có `GROQ_API_KEY`: thử `GroqLLMClient`.
2. Nếu có `OPENAI_API_KEY`: thử `OpenAILLMClient`.
3. Nếu lỗi hoặc thiếu key: dùng `MockLLMClient`.

Chưa hoàn thiện:

- `OpenAILLMClient.complete` luôn đặt `response_format={"type": "json_object"}`. Điều này phù hợp với một số prompt JSON nhưng không phù hợp tuyệt đối cho report HTML hoặc KPI Markdown.
- Exception khi khởi tạo real client bị nuốt và fallback mock, có thể làm khó debug nếu key sai.

#### `ai_layer/evidence_analyzer.py`

Luồng phân tích:

1. Phase 1: LLM sinh checklist từ tên/mô tả nhiệm vụ.
2. Nếu Phase 1 parse lỗi, fallback `_extract_requirements`.
3. Phase 2: LLM đối chiếu checklist với nội dung tài liệu.
4. `_parse_ai_response` parse JSON, sanitize checklist, tính score từ deduction, strengths/weaknesses.
5. Nếu lỗi tổng thể, trả result score 0.

Chưa hoàn thiện:

- Prompt chính nằm inline trong code; file `evidence_analyzer_prompt.txt` tồn tại nhưng không được dùng bởi analyzer hiện tại.
- Logic sanitize có heuristic keyword, có thể loại nhầm tiêu chí.

#### Prompt Files

| File | Vai trò | Được dùng thực tế |
| --- | --- | --- |
| `prompts/kpi_explainer_prompt.txt` | Prompt giải thích KPI, nhấn mạnh không tự tính điểm | Có, bởi `KPIExplainer` |
| `prompts/report_generator_prompt.txt` | Prompt sinh report HTML | Có, bởi `ReportGenerator` |
| `prompts/chatbot_copilot_prompt.txt` | Prompt chatbot lãnh đạo | Chưa hoàn thiện: service build prompt inline, chưa đọc file |
| `prompts/evidence_analyzer_prompt.txt` | Prompt JSON evidence analyzer | Chưa hoàn thiện: analyzer hiện dùng prompt inline two-phase |

### RAG Layer

| File | Mục đích | Ai gọi | Gọi ai | Nếu xoá |
| --- | --- | --- | --- | --- |
| `rag/document_loader.py` | Extract text từ txt/md/csv/pdf/docx/xlsx | `GraphRAGService` | Docling, pypdf, docx, pandas | Không index text evidence được |
| `rag/chunker.py` | Chia text thành chunk 900 chars overlap 120 | `GraphRAGService` | Không | Không tạo chunk cho vector |
| `rag/embedding_client.py` | Mock embedding hoặc bge-m3 | `GraphRAGService`, `PGVectorStore` | sentence-transformers nếu real | Không có vector để search |
| `rag/pgvector_store.py` | Lưu/query `document_chunks` bằng cosine distance | `GraphRAGService` | SQLAlchemy, pgvector | Vector RAG mất |
| `rag/kuzu_graph_store.py` | Embedded graph schema/upsert/link/query context | `GraphRAGService`, seed script | Kùzu | Graph context mất |
| `rag/graph_rag_service.py` | Orchestrator RAG: extract, chunk, embed, save vector, sync graph, retrieve context | `EvidenceService`, `ChatbotService` | Loader, chunker, embedding, vector, graph | Pipeline RAG mất |
| `rag/__init__.py` | Package marker | Import system | Không | Có thể ảnh hưởng import |

#### GraphRAG Flow Khi Upload

```text
TaskEvidence row
  -> DocumentLoader.extract_text(file_path)
  -> TextChunker.split(text)
  -> EmbeddingClient.embed_texts(chunks)
  -> PGVectorStore.add_chunks(document_chunks)
  -> evidence.extracted_text = text
  -> KuzuGraphStore upsert Evidence/Task/Chunk
  -> link Task-Evidence, User-Task, Evidence-Chunk
```

#### GraphRAG Flow Khi Chat

```text
Question
  -> ChatbotService.detect_intent
  -> structured SQL data
  -> GraphRAGService.build_chat_context
  -> PGVectorStore similarity_search
  -> KuzuGraphStore find_*_context
  -> LLM prompt
  -> answer + sources
```

Chưa hoàn thiện:

- Graph schema có Department/User/Criterion methods nhưng upload sync không tự upsert department/user/criterion đầy đủ, seed script mới sync phần cơ bản.
- `TASK_MEASURED_BY` và `CHUNK_SUPPORTS_CRITERION` có method nhưng chưa thấy service chính link tự động.
- Nếu Kùzu import lỗi, store im lặng `available=False`, app vẫn chạy nhưng graph context rỗng.

### Database Models

| File | Bảng/classes | Vai trò | Nếu xoá |
| --- | --- | --- | --- |
| `models/departments.py` | `Department` | Phòng ban và cây cha-con | Mất tổ chức phòng ban |
| `models/users.py` | `User` | Cán bộ, role, template KPI, phòng ban | Mất user và selector |
| `models/tasks.py` | `Task`, `TaskAssignment` | Nhiệm vụ và giao nhiệm vụ | Mất task management/KPI task score |
| `models/evidences.py` | `TaskEvidence` | File minh chứng và kết quả AI | Mất evidence pipeline |
| `models/kpi.py` | `KPITemplate`, `KPICriterion`, `DocumentTypeRule`, `KPIScore` | Template/rule/score KPI | Mất KPI engine data |
| `models/rag.py` | `DocumentChunk` | Vector chunks pgvector | Mất vector RAG |
| `models/chat.py` | `ChatLog` | Lưu lịch sử chatbot | Mất log hội thoại |
| `models/reports.py` | `Report` | Báo cáo đã sinh | Mất report list/preview |
| `models/__init__.py` | Import toàn bộ models | Đảm bảo `create_all` biết models | Init DB có thể thiếu bảng |

### Schemas

| File | Schema | Vai trò | Nếu xoá |
| --- | --- | --- | --- |
| `schemas/users.py` | `UserBase`, `UserOut` | Kiểu dữ liệu user | Một số route/docs type mất |
| `schemas/departments.py` | `DepartmentOut` | Kiểu dữ liệu phòng ban | Docs/type mất |
| `schemas/tasks.py` | `TaskCreate`, `TaskUpdate`, `TaskStatusUpdate`, `TaskOut` | Request body task | Task POST/PATCH không validate |
| `schemas/evidences.py` | `EvidenceOut`, `EvidenceAnalysisOut` | Output evidence | Docs/type mất; route hiện trả dict thủ công |
| `schemas/kpi.py` | `KPIScoreOut`, `KPICriterionOut` | Output KPI | Docs/type mất; route hiện trả dict thủ công |
| `schemas/chatbot.py` | `ChatbotMessageIn`, `ChatbotMessageOut` | Input/output chatbot | Chatbot POST không nhận body typed |
| `schemas/reports.py` | `ReportGenerateIn`, `ReportOut` | Input/output report | Generate report không validate |
| `schemas/__init__.py` | Package marker | Import system | Có thể ảnh hưởng import |

### Scripts

| File | Vai trò | Ai chạy | Nếu xoá |
| --- | --- | --- | --- |
| `scripts/seed_from_excel.py` | Gọi `ExcelRuleLoader.seed()` để seed KPI templates/rules | CLI setup | Không seed rule KPI/doc type |
| `scripts/seed_demo_data.py` | Reset business data, seed 5 departments, 38 users, 194 tasks, 60 evidences, chunks, KPI scores, chat logs, reports, sync graph | CLI setup/demo | Không có dữ liệu demo |
| `scripts/smoke_test_api.py` | Gọi vài endpoint health/users/dashboard/task stats | CLI smoke test | Mất check nhanh API |

Chưa hoàn thiện:

- Smoke test chỉ kiểm tra 4 endpoint và dùng `print`, chưa là test suite.
- Seed demo có dữ liệu hardcode phục vụ dashboard, không phản ánh DB production.

## 6. Database

### Danh Sách Bảng

- `departments`
- `users`
- `kpi_templates`
- `kpi_criteria`
- `document_type_rules`
- `tasks`
- `task_assignments`
- `task_evidences`
- `document_chunks`
- `kpi_scores`
- `chat_logs`
- `reports`

### Phân Tích Từng Bảng

#### `departments`

Mục đích: lưu phòng ban và quan hệ cha-con.

| Cột | Ý nghĩa |
| --- | --- |
| `id` | Khóa chính |
| `name` | Tên phòng/đơn vị |
| `code` | Mã phòng, unique |
| `parent_id` | Phòng cha |

Quan hệ: `Department.users`, self-parent.

#### `users`

Mục đích: cán bộ demo.

| Cột | Ý nghĩa |
| --- | --- |
| `id` | Khóa chính |
| `full_name` | Họ tên |
| `email` | Email unique |
| `role` | `LEADER`, `MANAGER`, `STAFF` |
| `kpi_role_template` | Mã template KPI |
| `department_id` | Phòng ban |
| `position_title` | Chức danh |
| `avatar_url` | Avatar |
| `is_active` | Trạng thái active |

Quan hệ: thuộc `departments`, có task assignments, KPI scores, chat logs, reports created_by.

#### `kpi_templates`

Mục đích: template KPI theo vai trò.

| Cột | Ý nghĩa |
| --- | --- |
| `id` | Khóa chính |
| `code` | Mã template |
| `name` | Tên template |
| `target_role` | Vai trò áp dụng |
| `total_score` | Tổng điểm, default 100 |

Quan hệ: 1-n với `kpi_criteria`, được `users.kpi_role_template` tham chiếu bằng code và `kpi_scores.template_id` tham chiếu bằng id.

#### `kpi_criteria`

Mục đích: nhóm tiêu chí KPI và max score.

| Cột | Ý nghĩa |
| --- | --- |
| `id` | Khóa chính |
| `template_id` | Template cha |
| `group_code` | Mã nhóm I/II/... |
| `group_name` | Tên nhóm |
| `criterion_code` | Mã tiêu chí |
| `criterion_name` | Tên tiêu chí |
| `description` | Mô tả |
| `calculation_rule_text` | Rule text |
| `max_score` | Điểm tối đa |
| `sort_order` | Thứ tự |

Quan hệ: thuộc `kpi_templates`.

#### `document_type_rules`

Mục đích: mô tả nhóm văn bản A/B/C/D.

| Cột | Ý nghĩa |
| --- | --- |
| `id` | Khóa chính |
| `code` | A/B/C/D |
| `name` | Tên nhóm |
| `description` | Mô tả loại văn bản |
| `scoring_rule_text` | Rule text |

Quan hệ: hiện không có FK trực tiếp; `tasks.document_type` lưu code.

#### `tasks`

Mục đích: nhiệm vụ công việc.

| Cột | Ý nghĩa |
| --- | --- |
| `id` | Khóa chính |
| `title` | Tên nhiệm vụ |
| `description` | Mô tả |
| `creator_id` | Người tạo |
| `department_id` | Phòng liên quan |
| `deadline` | Hạn xử lý |
| `weight` | Trọng số |
| `document_type` | A/B/C/D |
| `status` | `NOT_STARTED`, `IN_PROGRESS`, `COMPLETED`, `OVERDUE` |
| `priority` | `LOW`, `MEDIUM`, `HIGH` |
| `created_at` | Ngày tạo |
| `updated_at` | Ngày cập nhật |

Quan hệ: 1-n `task_assignments`, 1-n `task_evidences`.

#### `task_assignments`

Mục đích: giao nhiệm vụ cho cán bộ.

| Cột | Ý nghĩa |
| --- | --- |
| `id` | Khóa chính |
| `task_id` | Nhiệm vụ |
| `user_id` | Cán bộ |
| `progress_percent` | Tiến độ |
| `self_score` | Điểm tự đánh giá |
| `leader_score` | Điểm lãnh đạo đánh giá |
| `final_score` | Điểm cuối |

Quan hệ: thuộc `Task`, liên kết `User`.

#### `task_evidences`

Mục đích: file minh chứng.

| Cột | Ý nghĩa |
| --- | --- |
| `id` | Khóa chính |
| `task_id` | Nhiệm vụ |
| `uploaded_by` | Người upload |
| `file_name` | Tên file gốc |
| `file_type` | MIME type |
| `file_path` | Path local |
| `extracted_text` | Nội dung trích xuất |
| `ai_relevance_score` | Điểm phù hợp AI |
| `ai_summary` | Tóm tắt AI |
| `ai_missing_points` | JSON string checklist/strength/weakness |
| `status` | `UPLOADED`, `PROCESSING`, `ANALYZED`, `FAILED` |
| `created_at` | Ngày tạo |

Quan hệ: thuộc `Task`, có `document_chunks`.

#### `document_chunks`

Mục đích: chunks văn bản phục vụ Vector RAG.

| Cột | Ý nghĩa |
| --- | --- |
| `id` | Khóa chính |
| `evidence_id` | Minh chứng |
| `task_id` | Nhiệm vụ |
| `chunk_index` | Thứ tự chunk |
| `content` | Nội dung chunk |
| `embedding` | Vector 1024 chiều |
| `metadata_json` | Metadata JSON |
| `created_at` | Ngày tạo |

Quan hệ: thuộc evidence/task; query bằng cosine distance.

#### `kpi_scores`

Mục đích: điểm KPI đã tính/lưu.

| Cột | Ý nghĩa |
| --- | --- |
| `id` | Khóa chính |
| `user_id` | Cán bộ |
| `period_month` | Kỳ tháng |
| `template_id` | Template |
| `total_score` | Tổng điểm |
| `classification` | Xếp loại |
| `breakdown_json` | Breakdown rule engine |
| `ai_explanation` | Giải thích AI |
| `risk_level` | LOW/MEDIUM/HIGH |
| `created_at` | Ngày tạo |

#### `chat_logs`

Mục đích: lịch sử câu hỏi chatbot.

| Cột | Ý nghĩa |
| --- | --- |
| `id` | Khóa chính |
| `user_id` | Người hỏi |
| `question` | Câu hỏi |
| `intent` | Intent detect |
| `answer` | Câu trả lời |
| `sources_json` | Sources từ vector context |
| `created_at` | Ngày tạo |

#### `reports`

Mục đích: báo cáo đã sinh.

| Cột | Ý nghĩa |
| --- | --- |
| `id` | Khóa chính |
| `report_type` | WEEKLY/MONTHLY/... |
| `period` | Kỳ báo cáo |
| `department_id` | Phòng nếu có |
| `content` | HTML/text report |
| `summary_json` | Structured data dùng sinh báo cáo |
| `created_by` | Người tạo |
| `created_at` | Ngày tạo |

## 7. API Inventory

| Method | URL | Chức năng | Service liên quan |
| --- | --- | --- | --- |
| GET | `/health` | Health check app | `main.py` |
| GET | `/api/users` | Danh sách cán bộ | DB direct |
| GET | `/api/users/by-department/{department_id}` | Cán bộ theo phòng | DB direct |
| GET | `/api/users/{user_id}` | Chi tiết cán bộ | DB direct |
| GET | `/api/departments` | Danh sách phòng ban | DB direct |
| GET | `/api/departments/{department_id}/users` | Users trong phòng | DB direct |
| GET | `/api/tasks` | List/filter tasks | DB direct |
| POST | `/api/tasks` | Tạo nhiệm vụ | `TaskService.create` |
| GET | `/api/tasks/stats` | Thống kê trạng thái task | DB direct |
| GET | `/api/tasks/{task_id}` | Chi tiết task | DB direct |
| PATCH | `/api/tasks/{task_id}` | Sửa task | `TaskService.update` |
| DELETE | `/api/tasks/{task_id}` | Xoá task | DB direct |
| PATCH | `/api/tasks/{task_id}/status` | Cập nhật status/progress | DB direct |
| POST | `/api/evidences/upload` | Upload + process evidence | `EvidenceService.upload_and_process` |
| GET | `/api/evidences` | List/filter evidences | DB direct |
| GET | `/api/evidences/{evidence_id}` | Chi tiết evidence | DB direct |
| POST | `/api/evidences/{evidence_id}/analyze` | Phân tích lại evidence | `EvidenceService.analyze` |
| GET | `/api/evidences/{evidence_id}/analysis` | Lấy kết quả analysis | DB direct |
| GET | `/api/kpi/dashboard` | Dashboard tổng quan | DB direct |
| GET | `/api/kpi/heatmap` | Heatmap phòng ban | DB direct |
| GET | `/api/kpi/users/{user_id}/profile` | Hồ sơ cán bộ | DB direct |
| GET | `/api/kpi/users/{user_id}/score` | Điểm KPI, auto recompute nếu chưa có | `KPIEngine` |
| POST | `/api/kpi/users/{user_id}/score/recompute` | Tính lại KPI | `KPIEngine` |
| GET | `/api/kpi/criteria` | Tiêu chí KPI, filter role_template | DB direct |
| GET | `/api/kpi/ranking` | Ranking KPI | DB direct |
| POST | `/api/chatbot/message` | Chatbot leadership copilot | `ChatbotService` |
| POST | `/api/reports/generate` | Sinh report | `ReportService` |
| GET | `/api/reports` | List reports | DB direct |
| GET | `/api/reports/{report_id}` | Chi tiết report | DB direct |

Input/output chính:

- `/api/tasks`: query `status`, `department_id`, `assigned_user_id`, `month`. Output task dict gồm assignees và evidence_count.
- `/api/evidences`: query `uploaded_by`, `task_id`. Output evidence dict.
- `/api/kpi/users/{id}/score`: query `month`; output `total_score`, `classification`, `risk_level`, `breakdown_json`, `ai_explanation`.
- `/api/chatbot/message`: body `{user_id, message, month, department_id}`; output `{answer, intent, data, sources}`.
- `/api/reports/generate`: body `{report_type, period, department_id, created_by}`; output report dict.

## 8. Phân Tích Frontend

### Cấu Trúc Frontend

```text
frontend/src/
├── App.jsx
├── main.jsx
├── api/
│   ├── client.js
│   ├── userApi.js
│   ├── taskApi.js
│   ├── evidenceApi.js
│   ├── kpiApi.js
│   ├── chatbotApi.js
│   └── reportApi.js
├── layouts/
│   └── AppLayout.jsx
├── pages/
│   ├── DashboardPage.jsx
│   ├── HeatmapPage.jsx
│   ├── EmployeeProfilePage.jsx
│   ├── TasksPage.jsx
│   ├── EvidencesPage.jsx
│   ├── EvidenceAnalysisPage.jsx
│   ├── KpiEvaluationPage.jsx
│   ├── CopilotChatPage.jsx
│   └── ReportsPage.jsx
├── components/
│   ├── ChatBox.jsx
│   ├── EvidenceTable.jsx
│   ├── KpiDonutChart.jsx
│   ├── KpiTrendChart.jsx
│   ├── OrgHeatmap.jsx
│   ├── ReportPreview.jsx
│   ├── StatCard.jsx
│   ├── StatusTag.jsx
│   └── TaskTable.jsx
├── styles/theme.css
└── utils/formatters.js
```

### Frontend Entry Và Layout

| File | Mục đích | Ai gọi | Gọi ai | Nếu xoá |
| --- | --- | --- | --- | --- |
| `main.jsx` | Mount React app, cấu hình AntD locale/theme | Browser Vite entry | `App`, `theme.css` | Frontend không mount |
| `App.jsx` | Khai báo routes | `main.jsx` | Pages, `AppLayout` | Không điều hướng được |
| `layouts/AppLayout.jsx` | Sidebar navy, menu, header selector cán bộ grouped theo phòng ban, localStorage selected user | `App.jsx` | `userApi`, routes outlet | Mất layout/menu/user selector |
| `styles/theme.css` | CSS shell, cards, heatmap, chatbox, reports | Browser | CSS | UI mất style chính |
| `utils/formatters.js` | Mapping status/role/template/risk và format date/color | Components/pages | Không | UI lộ enum tiếng Anh và thiếu format |

### API Client

| File | Mục đích | Endpoint |
| --- | --- | --- |
| `api/client.js` | Axios instance, baseURL từ `VITE_API_BASE_URL` hoặc fallback `http://localhost:8000/api` | Tất cả |
| `api/userApi.js` | Users/departments API | `/users`, `/departments` |
| `api/taskApi.js` | Task list/stats/create/update/delete/status | `/tasks` |
| `api/evidenceApi.js` | Evidence list/get/analysis/analyze/upload | `/evidences` |
| `api/kpiApi.js` | Dashboard/heatmap/profile/score/recompute/criteria/ranking | `/kpi` |
| `api/chatbotApi.js` | Chatbot message | `/chatbot/message` |
| `api/reportApi.js` | Report list/generate/get | `/reports` |

Nếu xoá một API file, page/component tương ứng sẽ không gọi backend được.

### Màn Hình Hiện Có

| Page | Route | Chức năng | API dùng | Component liên quan |
| --- | --- | --- | --- | --- |
| `DashboardPage.jsx` | `/dashboard` | Tổng cán bộ, KPI trung bình, task completed/overdue, top/low KPI, donut task status, trend demo | `kpiApi.dashboard` | `StatCard`, `KpiDonutChart`, `KpiTrendChart` |
| `HeatmapPage.jsx` | `/heatmap` | KPI trung bình theo phòng ban | `kpiApi.heatmap` | `OrgHeatmap` |
| `EmployeeProfilePage.jsx` | `/employees/:userId` | Hồ sơ cán bộ, role/template/risk tiếng Việt, task liên quan | `kpiApi.profile` | `TaskTable` |
| `TasksPage.jsx` | `/tasks` | List tasks, modal tạo nhiệm vụ, giao cho user grouped theo phòng ban | `taskApi.list/create`, `userApi.list/departments` | `TaskTable` |
| `EvidencesPage.jsx` | `/evidences` | Upload minh chứng theo selected user, list evidence của selected user | `evidenceApi.list/upload`, `taskApi.list` | `EvidenceTable` |
| `EvidenceAnalysisPage.jsx` | `/evidences/:evidenceId/analysis` | Xem extracted text, score, summary, checklist, strengths/weaknesses, phân tích lại | `evidenceApi.analysis/analyze` | AntD cards/list/progress |
| `KpiEvaluationPage.jsx` | `/kpi/:userId` | Xem/tính lại KPI, breakdown rule engine | `kpiApi.score/recompute` | AntD Descriptions/Table |
| `CopilotChatPage.jsx` | `/copilot` | Chat với AI Copilot, xem structured data trả về | `chatbotApi.send` | `ChatBox` |
| `ReportsPage.jsx` | `/reports` | List report, sinh report, preview HTML | `reportApi.list/generate` | `ReportPreview` |

Chưa hoàn thiện FE:

- Không có auth/login thật; selected user lưu localStorage.
- Nhiều page không có loading/error state đầy đủ; nếu CORS/API lỗi có thể render trống.
- `KpiTrendChart` dùng data demo hardcode nếu không truyền data.
- `ReportPreview` dùng `dangerouslySetInnerHTML`; cần sanitize nếu nhận HTML không tin cậy.

### Components

| Component | Mục đích | Props | API liên quan | Nếu xoá |
| --- | --- | --- | --- | --- |
| `StatCard.jsx` | Card statistic có icon | `title`, `value`, `suffix`, `precision`, `icon` | Không trực tiếp | Dashboard thiếu stat cards |
| `StatusTag.jsx` | Hiển thị tag trạng thái task/evidence | `status` | Không trực tiếp | Bảng mất tag trạng thái |
| `TaskTable.jsx` | Bảng nhiệm vụ | `data`, `loading` | Nhận data từ pages | Tasks/profile mất bảng task |
| `EvidenceTable.jsx` | Bảng minh chứng, link analysis | `data`, `loading` | Nhận data từ `EvidencesPage` | Evidence list mất |
| `KpiDonutChart.jsx` | Donut chart task status | `data` | Dashboard data | Dashboard mất chart trạng thái |
| `KpiTrendChart.jsx` | Area chart xu hướng KPI | `data` optional, default demo | Không trực tiếp | Dashboard mất chart trend |
| `OrgHeatmap.jsx` | Grid heatmap phòng ban | `data` | Heatmap data | Heatmap mất UI chính |
| `ChatBox.jsx` | Chat input/list message | `onSend`, `loading` | Indirect qua parent | Copilot chat mất box |
| `ReportPreview.jsx` | Preview report HTML | `report` | Reports data | Reports mất preview |

## 9. AI & RAG

### LLM Layer

Model mặc định trong config:

- `openai_model`: `gpt-4o-mini`.
- `groq_model`: `llama-3.3-70b-versatile`.
- Nếu `OPENAI_BASE_URL` chứa `openrouter.ai`, client thêm headers `HTTP-Referer` và `X-Title`.
- Nếu không có key hoặc client lỗi, fallback `MockLLMClient`.

Luồng gọi model:

```text
Service/AI helper
  -> get_llm_client()
  -> GroqLLMClient hoặc OpenAILLMClient hoặc MockLLMClient
  -> complete(prompt, system_prompt)
```

### KPI Explainer

Mục đích: giải thích điểm đã được `KPIEngine` tính. LLM không được tự tính lại điểm.

Đầu vào: payload KPI gồm user_id, period, total_score, classification, risk_level, breakdown, raw_reasons.

Đầu ra: text/Markdown giải thích KPI lưu vào `kpi_scores.ai_explanation`.

Prompt: `backend/ai_layer/prompts/kpi_explainer_prompt.txt`.

### Evidence Analyzer

Mục đích: đánh giá file minh chứng có phù hợp nhiệm vụ không.

Đầu vào:

- Tên/mô tả nhiệm vụ.
- Nội dung file trích xuất.
- Người upload, phòng ban, hạn chót, filename, file_type.

Đầu ra:

- `relevance_score`
- `summary`
- `checklist`
- `strengths`
- `weaknesses`

Chưa hoàn thiện: prompt file riêng chưa được dùng; logic prompt nằm inline.

### Chatbot Copilot

Luồng thực tế:

```text
User question
  -> /api/chatbot/message
  -> ChatbotService.detect_intent
  -> PostgreSQL structured query
  -> GraphRAGService.build_chat_context
  -> LLM answer
  -> ChatLog
```

Các câu hỏi hỗ trợ tốt nhất theo keyword:

- "Ai có nguy cơ không đạt KPI?"
- "Phòng nào đang chậm tiến độ?"
- "Vì sao cán bộ A bị điểm thấp?"
- "Sinh báo cáo giao ban tuần này."

Chưa hoàn thiện:

- Multi-turn memory chưa có; chỉ lưu log.
- Không có retrieval theo tên cán bộ cụ thể trong `EMPLOYEE_PROFILE`.
- Không có tool/action generate report thật từ chatbot; intent chỉ ảnh hưởng structured data/prompt.

### GraphRAG

Dữ liệu đầu vào: file minh chứng đã upload.

Dữ liệu vector:

- Chunks lưu trong PostgreSQL bảng `document_chunks`.
- Embedding 1024 chiều.
- Query cosine distance qua pgvector.

Dữ liệu graph:

- KùzuDB local path `backend/storage/kuzu_db`.
- Nodes: User, Department, Task, Evidence, Criterion, Chunk.
- Relationships: USER_BELONGS_TO, USER_ASSIGNED_TASK, TASK_HAS_EVIDENCE, EVIDENCE_HAS_CHUNK, ...

Context sinh ra:

- `vectors`: danh sách chunk gần nhất.
- `graph`: list dict từ query Kùzu.

Chưa hoàn thiện:

- Graph context hiện còn thô, keys dạng `col_0`, `col_1`.
- Không có reranker.
- Không có metadata filter nâng cao theo department/user trong mọi nhánh.

## 10. Những Gì Đã Hoàn Thành

- [x] FastAPI backend chạy được.
- [x] PostgreSQL models cho business data.
- [x] pgvector `document_chunks`.
- [x] KùzuDB embedded graph store có schema/upsert/link/query.
- [x] GraphRAG indexing evidence.
- [x] Mock embedding và bge-m3 optional.
- [x] MockLLM fallback và OpenAI/Groq-compatible clients.
- [x] KPI Rule Engine.
- [x] AI KPI explanation.
- [x] Evidence upload + extraction + chunk + embed + analyze.
- [x] Chatbot endpoint và UI chat.
- [x] Report generation endpoint và UI preview.
- [x] React/Vite/Ant Design 9 màn hình.
- [x] Seed demo 38 users, 194 tasks, 60 evidences, KPI scores, reports.
- [x] Docker compose PostgreSQL pgvector.

## 11. Những Gì Chưa Hoàn Thiện

- [ ] Auth/JWT/permission model chưa có.
- [ ] Excel rule loader chưa parse chi tiết Excel; hiện seed theo spec hardcode và chỉ mở thử file.
- [ ] KPI Engine chưa filter task theo period khi recompute.
- [ ] Chatbot chưa có multi-turn memory ngoài `chat_logs`.
- [ ] Chatbot chưa dùng prompt file `chatbot_copilot_prompt.txt`.
- [ ] Evidence analyzer chưa dùng prompt file `evidence_analyzer_prompt.txt`.
- [ ] Report export PDF/DOCX chưa có.
- [ ] Không có migration tool như Alembic.
- [ ] Không có test suite tự động đầy đủ; chỉ smoke test rất nhỏ.
- [ ] Không có audit log, notification, approval workflow.
- [ ] Không có queue/background worker; upload xử lý sync.
- [ ] Chưa có real production vector/RAG evaluation.
- [ ] Graph relationship `TASK_MEASURED_BY` và `CHUNK_SUPPORTS_CRITERION` chưa được link tự động trong luồng chính.
- [ ] UI error/loading state chưa đầy đủ.

## 12. Rủi Ro Kỹ Thuật

- CORS phụ thuộc `CORS_ORIGINS`; nếu Vite đổi port, FE có thể gọi API `200 OK` ở backend nhưng browser chặn response.
- `.env` chứa key thật trong môi trường dev có rủi ro bảo mật; nên rotate key nếu đã chia sẻ.
- Không có auth nên mọi endpoint có thể thao tác dữ liệu nếu truy cập được backend.
- Rule KPI hiện là heuristic PoC, không phải rule pháp lý/Excel chi tiết.
- LLM response format hiện ép JSON object trong `OpenAILLMClient`, có thể không phù hợp prompt HTML/Markdown.
- `ReportPreview` render HTML trực tiếp.
- `EvidenceService` có `traceback.print_exc()` và rollback/recreate evidence khi lỗi.
- Kùzu optional silent fail: nếu import/init lỗi, graph context rỗng nhưng app không báo rõ.
- Seed scripts truncate nhiều bảng; không dùng trên dữ liệu thật.
- Không có transaction boundary phức tạp hoặc retry cho LLM/vector/graph.
- Không có cache, rate limiting, pagination server-side toàn diện.
- Không có DB indexes đầy đủ ngoài các index cơ bản trong model.

## 13. TODO / Dấu Hiệu Chưa Hoàn Thiện Trong Source

Không phát hiện TODO/FIXME rõ ràng. Các dấu hiệu PoC/chưa hoàn thiện phát hiện qua code:

- `frontend/src/components/KpiTrendChart.jsx`: chart trend dùng data demo hardcode.
- `backend/services/excel_rule_loader.py`: `_touch_excel_files` nuốt lỗi bằng `pass`, chưa parse rule Excel chi tiết.
- `backend/services/evidence_service.py`: dùng `traceback.print_exc()`.
- `backend/scripts/smoke_test_api.py`: dùng `print`, chỉ smoke 4 endpoint.
- `backend/ai_layer/llm_client.py`: fallback silent sang mock nếu client thật lỗi.
- `backend/ai_layer/rag/document_loader.py`: nhiều định dạng fallback text "chưa trích xuất được".
- `backend/services/extractor.py`: utility lớn nhưng chưa được pipeline chính gọi.

## 14. Hướng Dẫn Cho AI Agent Tiếp Theo

### File Quan Trọng Nhất

1. `backend/main.py`: biết app mount route nào, port nào, CORS ra sao.
2. `backend/core/config.py`: biết config/env/storage/LLM/DB.
3. `backend/db/models/*.py`: hiểu schema dữ liệu.
4. `backend/api/routes/*.py`: hiểu API surface.
5. `backend/services/kpi_engine.py`: hiểu rule tính KPI.
6. `backend/services/evidence_service.py`: hiểu upload/minh chứng/AI/RAG.
7. `backend/services/chatbot_service.py`: hiểu chatbot intent + data + RAG.
8. `backend/ai_layer/rag/graph_rag_service.py`: hiểu RAG orchestration.
9. `frontend/src/App.jsx`: hiểu routes frontend.
10. `frontend/src/layouts/AppLayout.jsx`: hiểu selector user/localStorage/menu.

### Service Quan Trọng Nhất

- `KPIEngine`: nguồn sự thật của điểm KPI.
- `EvidenceService`: pipeline minh chứng end-to-end.
- `GraphRAGService`: cầu nối document extraction, vector store, graph store.
- `ChatbotService`: intent, SQL structured data, GraphRAG context, LLM answer.
- `ReportService`: dữ liệu báo cáo và lưu report.

### Luồng Xử Lý Quan Trọng

Upload evidence:

```text
FE EvidencesPage
  -> evidenceApi.upload
  -> POST /api/evidences/upload
  -> EvidenceService.upload_and_process
  -> FileStorage.save_upload
  -> GraphRAGService.index_evidence
  -> EvidenceAnalyzer.analyze
  -> task_evidences status ANALYZED
```

Recompute KPI:

```text
FE KpiEvaluationPage
  -> kpiApi.recompute
  -> POST /api/kpi/users/{id}/score/recompute
  -> KPIEngine.compute_user_score
  -> KPIExplainer.explain
  -> upsert kpi_scores
```

Chatbot:

```text
FE CopilotChatPage
  -> chatbotApi.send
  -> ChatbotService.answer
  -> detect_intent + SQL data
  -> GraphRAGService.build_chat_context
  -> LLM complete
  -> ChatLog
```

Report:

```text
FE ReportsPage
  -> reportApi.generate
  -> ReportService.generate
  -> collect DB stats
  -> ReportGenerator.generate
  -> reports table
```

### Các Điểm Cần Cẩn Thận Khi Sửa

- Không để LLM tính điểm KPI; mọi điểm phải đi qua `KPIEngine`.
- Nếu đổi port frontend, cập nhật `backend/.env CORS_ORIGINS`.
- Nếu đổi dimension embedding, phải đổi `DocumentChunk.embedding vector(1024)` và dữ liệu cũ.
- Nếu bật `USE_REAL_EMBEDDINGS=true`, máy cần tải/có model `BAAI/bge-m3`.
- Nếu sửa `TaskAssignment`, kiểm tra `KPIEngine`, `PGVectorStore.similarity_search_by_user`, seed script.
- Nếu sửa response shape API, cập nhật API client và pages tương ứng.
- Nếu sửa prompt report/KPI, nhớ `OpenAILLMClient` đang ép JSON object.
- Không chạy `seed_demo_data.py` trên DB có dữ liệu cần giữ vì script truncate nhiều bảng.

### Thứ Tự Nên Đọc Source

1. `README.md`, `backend/README.md` nếu cần setup.
2. `backend/main.py`.
3. `backend/core/config.py`.
4. `backend/db/models/*.py`.
5. `backend/api/routes/*.py`.
6. `backend/services/kpi_engine.py`.
7. `backend/services/evidence_service.py`.
8. `backend/ai_layer/rag/graph_rag_service.py`.
9. `backend/services/chatbot_service.py`.
10. `frontend/src/App.jsx`.
11. `frontend/src/layouts/AppLayout.jsx`.
12. `frontend/src/pages/*.jsx`.

## 15. Ghi Chú Product/Tech Lead

Hệ thống hiện là PoC chạy end-to-end, không phải production-ready. Phần đáng giá nhất của PoC là chứng minh được chuỗi:

```text
Dashboard
-> Task Management
-> Upload Evidence
-> Extract Text
-> Vector Index
-> Graph Index
-> AI Evidence Analysis
-> KPI Recompute
-> Leadership Chatbot
-> Auto Report
```

Để nâng lên production, ưu tiên:

1. Chuẩn hóa rule KPI từ Excel thật.
2. Thêm auth/permission/audit.
3. Thêm migrations và test suite.
4. Chuẩn hóa LLM output format theo từng use case.
5. Làm rõ graph schema và relationship criterion.
6. Thêm observability cho LLM/RAG failures.
7. Tách seed demo khỏi vận hành thật.
