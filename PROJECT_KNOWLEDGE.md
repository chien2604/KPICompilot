# Project Knowledge

Tài liệu này phản ánh source sau đợt chuẩn hóa dữ liệu nhân sự xã Nghĩa Lâm.

## 1. Luồng hệ thống

```text
React + Ant Design
  -> FastAPI routes
  -> services / repositories
  -> PostgreSQL + pgvector
  -> local uploads + KùzuDB
  -> LLM cho phân tích, giải thích, hội thoại và báo cáo
```

PostgreSQL là nguồn dữ liệu chuẩn. KùzuDB là graph index phục vụ truy hồi quan hệ, không thay thế dữ liệu nghiệp vụ PostgreSQL.

## 2. Backend

### Entry và core

| File | Vai trò |
| --- | --- |
| `backend/main.py` | Tạo FastAPI app, CORS, đăng ký router và chạy Uvicorn. |
| `core/config.py` | Nơi duy nhất cấu hình DB, AI, JWT, storage, đường dẫn XLS và tổ chức. |
| `core/deps.py` | Dependency lấy user hiện tại và kiểm tra JWT. |
| `core/security.py` | Hash/verify mật khẩu và tạo access token. |
| `core/organization.py` | Bốn template chức vụ, chuẩn hóa tên và ánh xạ chức vụ kiêm nhiệm. |
| `core/permissions.py` | Quyền xem, giao việc và chấm điểm theo cấp và cùng xóm. |
| `core/logging.py` | Cấu hình log ứng dụng. |

### Routes

| File | Vai trò |
| --- | --- |
| `api/routes/auth.py` | Đăng nhập, lấy identity, đổi mật khẩu, danh sách người có thể giao việc. |
| `api/routes/users.py` | Hồ sơ cán bộ, cấu hình tài khoản, vai trò, kích hoạt và reset mật khẩu. |
| `api/routes/departments.py` | Tổ chức gốc, danh sách xóm và nhân sự theo phạm vi quyền. |
| `api/routes/tasks.py` | CRUD nhiệm vụ, phân công, tiến độ, trạng thái và chấm assignment. |
| `api/routes/evidences.py` | Upload, truy vấn và phân tích minh chứng trong phạm vi quyền. |
| `api/routes/kpi.py` | Dashboard, heatmap, hồ sơ, ranking, criteria và KPI recompute. |
| `api/routes/chatbot.py` | Nhận câu hỏi Copilot của user đã xác thực. |
| `api/routes/conversations.py` | Tạo, đọc và soft-delete hội thoại thuộc user hiện tại. |
| `api/routes/reports.py` | Sinh, đọc và cập nhật báo cáo theo phạm vi tổ chức/xóm. |

### Services và repository

| File | Vai trò |
| --- | --- |
| `services/task_service.py` | Nghiệp vụ tạo/cập nhật task và assignment. |
| `services/evidence_service.py` | Điều phối lưu file, extract, RAG index và AI analysis. |
| `services/file_storage.py` | Lưu file upload an toàn vào local storage. |
| `services/extractor.py` | Extractor độc lập còn được giữ để tránh xóa khi chưa xác nhận hợp nhất. |
| `services/kpi_engine.py` | Tính KPI bằng rule; không gọi LLM để quyết định điểm. |
| `services/kpi_template_service.py` | Đồng bộ bốn template chức vụ; không tạo tiêu chí giả. |
| `services/chatbot_service.py` | Intent, scoped structured data, GraphRAG, prompt và conversation memory. |
| `services/report_service.py` | Tổng hợp số liệu PostgreSQL và điều phối sinh báo cáo. |
| `services/personnel_import_service.py` | Parse XLS, reset dữ liệu cũ, tạo xóm/cán bộ và đồng bộ KùzuDB. |
| `repositories/conversation_repository.py` | CRUD hội thoại, message và summary. |

### Database

| File | Vai trò |
| --- | --- |
| `db/database.py` | SQLAlchemy engine/session và pgvector extension. |
| `db/init_db.py` | Tạo extension và các bảng còn thiếu, không drop dữ liệu. |
| `db/models/departments.py` | Tổ chức gốc và xóm. |
| `db/models/users.py` | Hồ sơ nhân sự, tài khoản, chức vụ và cấp quyền. |
| `db/models/tasks.py` | Task và assignment. |
| `db/models/evidences.py` | File minh chứng và kết quả AI. |
| `db/models/kpi.py` | Template, criteria, loại văn bản và score. |
| `db/models/rag.py` | Chunk và embedding pgvector. |
| `db/models/chat.py` | Chat log, conversation, message và summary. |
| `db/models/reports.py` | Báo cáo được lưu. |
| `migrations/001_create_conversations.py` | Thêm bảng hội thoại. |
| `migrations/002_add_reports_updated_at.py` | Thêm thời điểm cập nhật report. |
| `migrations/003_add_village_personnel_fields.py` | Thêm unit type và trường hồ sơ XLS. |

### AI và RAG

| File | Vai trò |
| --- | --- |
| `ai_layer/llm_client.py` | OpenAI-compatible client và fallback không bịa dữ liệu khi thiếu key. |
| `ai_layer/evidence_analyzer.py` | Phân tích nội dung minh chứng bằng prompt. |
| `ai_layer/kpi_explainer.py` | Chỉ giải thích kết quả rule engine. |
| `ai_layer/report_generator.py` | Sinh nội dung báo cáo. |
| `ai_layer/report_docx_renderer.py` | Render báo cáo sang DOCX. |
| `ai_layer/rag/document_loader.py` | Extract PDF, DOCX, TXT, XLS và XLSX. |
| `ai_layer/rag/chunker.py` | Chia văn bản thành chunk. |
| `ai_layer/rag/embedding_client.py` | Embedding 1024 chiều hoặc bge-m3. |
| `ai_layer/rag/pgvector_store.py` | Ghi và tìm cosine similarity trong PostgreSQL. |
| `ai_layer/rag/kuzu_graph_store.py` | Schema, node, relation và graph query KùzuDB. |
| `ai_layer/rag/graph_rag_service.py` | Index evidence và ghép vector/graph context. |
| `ai_layer/prompts/*.txt` | System/user prompt tách khỏi source Python. |

### Scripts

| File | Vai trò |
| --- | --- |
| `scripts/import_personnel.py` | Chạy reset/import file XLS đã cấu hình. |
| `scripts/create_admin.py` | Tạo/cập nhật admin từ biến môi trường. |
| `scripts/sync_kpi_templates.py` | Đồng bộ bốn template chức vụ. |
| `scripts/migrate_reports_to_blocks.py` | Chuyển report cũ sang cấu trúc block khi cần. |
| `scripts/smoke_test_api.py` | Smoke test API thủ công. |

## 3. Frontend

| Nhóm file | Vai trò |
| --- | --- |
| `main.jsx`, `App.jsx` | Bootstrap React, router và provider. |
| `contexts/AuthContext.jsx` | Token, identity, login và logout. |
| `layouts/AppLayout.jsx` | Header, sidebar, menu theo quyền và outlet. |
| `api/client.js` | Axios base URL, bearer token và xử lý 401. |
| `api/*Api.js` | Client theo từng domain: auth, user, task, evidence, KPI, chatbot, conversation, report, admin. |
| `pages/LoginPage.jsx` | Đăng nhập email/mật khẩu thật; không còn user demo. |
| `pages/DashboardPage.jsx` | Dashboard theo scope organization, village hoặc personal. |
| `pages/HeatmapPage.jsx` | Cây tổ chức và KPI các xóm. |
| `pages/EmployeeProfilePage.jsx` | Toàn bộ hồ sơ XLS, task và KPI cán bộ. |
| `pages/TasksPage.jsx` | Nhiệm vụ nhận/giao và chấm assignment. |
| `pages/EvidencesPage.jsx`, `EvidenceAnalysisPage.jsx` | Upload, danh sách và kết quả phân tích minh chứng. |
| `pages/KpiEvaluationPage.jsx`, `KpiScoringPage.jsx` | Xem kết quả rule engine và chấm người thuộc quyền. |
| `pages/CopilotChatPage.jsx` | Hội thoại nhiều phiên thuộc user đăng nhập. |
| `pages/ReportsPage.jsx` | Sinh, xem và chỉnh báo cáo. |
| `pages/AdminPage.jsx` | Gán email/mật khẩu và kích hoạt hồ sơ đã import. |
| `components/Conversation*.jsx`, `ChatBox.jsx` | Sidebar và vùng chat. |
| `components/TaskTable.jsx`, `EvidenceTable.jsx` | Bảng nghiệp vụ dùng lại. |
| `components/OrgHeatmap.jsx` | Cây tổ chức tương tác. |
| `components/Kpi*.jsx`, `StatCard.jsx` | Biểu đồ và chỉ số; không dùng số liệu demo. |
| `components/Report*.jsx` | Preview và editor báo cáo. |
| `components/ProtectedRoute.jsx` | Chặn route chưa đăng nhập hoặc thiếu quyền. |
| `components/FloatingCopilot.jsx` | Truy cập Copilot nhanh. |
| `styles/theme.css` | Theme và responsive layout toàn ứng dụng. |
| `utils/formatters.js` | Nhãn tiếng Việt và format trạng thái/KPI. |

## 4. Dữ liệu import

`backend/storage/imports/personnel.xls` không commit vào Git. Import hiện tạo 1 tổ chức, 13 xóm và 36 hồ sơ. Email/mật khẩu không có trong XLS nên không được suy luận; admin cấu hình sau khi import.

## 5. File đã loại bỏ

- JSON debug và `backend/package-lock.json`: không được runtime sử dụng.
- Seed demo, seed password và importer tổ chức Sở cũ: tạo dữ liệu giả hoặc dùng schema cũ.
- Ba Excel KPI cũ và Excel tổ chức Sở cũ: không còn là nguồn dữ liệu được phê duyệt.
- Ba script tạo DOCX một lần: công cụ tạo tài liệu ngoài runtime.
- Docker `pdf-service`: trỏ tới thư mục không tồn tại và không thuộc kiến trúc hiện tại.

`services/extractor.py` chưa bị xóa vì có phần chức năng trùng `document_loader.py` nhưng chưa được xác nhận hợp nhất.
