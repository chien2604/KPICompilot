# AI KPI Copilot - UBND xã Nghĩa Lâm

Hệ thống quản lý cán bộ, nhiệm vụ, minh chứng và đánh giá KPI cho UBND xã
Nghĩa Lâm, tỉnh Nghệ An.

## Dữ liệu chính thức

- Danh sách 42 cán bộ: `Danh sách CB, CC , VC đến ngày 01.8.2026.xlsx`.
- Tiêu chí và 371 mã công việc: `DM công việc gửi kèm QĐ 15.6.xlsx`.
- 37 cán bộ thuộc phạm vi KPI; 5 viên chức Trung tâm Cung ứng dịch vụ công
  chưa có tiêu chí riêng nên chỉ tham gia danh bạ tổ chức.
- PostgreSQL lưu dữ liệu nghiệp vụ và vector; KùzuDB lưu quan hệ GraphRAG.
- KPI do `KPIEngine` tính theo quy tắc, LLM chỉ phân tích và giải thích.

## Phân quyền giao việc

| Nhóm | Được giao việc cho |
| --- | --- |
| Quản trị viên | Tất cả cán bộ |
| Lãnh đạo HĐND, UBND xã | Trưởng các đơn vị trực thuộc |
| Trưởng đơn vị | Phó trưởng đơn vị và chuyên viên trong đơn vị mình |
| Phó trưởng đơn vị | Chuyên viên trong đơn vị mình |
| Chuyên viên | Không có quyền giao việc |

## Cài backend

```bash
conda create -n kpi python=3.10 -y
conda activate kpi
cd backend
pip install -r requirements.txt
cp .env.example .env
```

Cài PostgreSQL 16 và pgvector trên máy, tạo database theo `DATABASE_URL` trong
`backend/.env`. Để triển khai production bằng container, repository đã có
Dockerfile cho frontend/backend và `compose.yaml`; xem [DOCKER.md](DOCKER.md).

Khởi tạo schema, migration và nhập dữ liệu:

```bash
python -m db.init_db
python migrations/001_create_conversations.py
python migrations/002_add_reports_updated_at.py
python migrations/003_add_village_personnel_fields.py
python migrations/004_add_commune_kpi_structure.py
python scripts/import_personnel.py
```

Import là thao tác thay dữ liệu tổ chức có chủ đích. Script kiểm tra đủ 42 cán
bộ, 371 mã công việc, tổng 30 điểm tiêu chí chung và công thức quy đổi trước khi
xóa dữ liệu cũ.

## Tạo tài khoản

Khai báo tài khoản quản trị trong `backend/.env`:

```dotenv
BOOTSTRAP_ADMIN_NAME=Quản trị viên hệ thống
BOOTSTRAP_ADMIN_EMAIL=admin@example.gov.vn
BOOTSTRAP_ADMIN_PASSWORD=mat-khau-toi-thieu-8-ky-tu
```

Chạy `python scripts/create_admin.py`. Để cấp tài khoản cho cán bộ, đăng nhập
bằng quản trị viên, mở màn `Quản trị`, chọn đúng hồ sơ đã import, bổ sung email
và mật khẩu rồi kích hoạt. Không tạo lại hồ sơ cán bộ.

## Chạy ứng dụng

Backend tại cổng `8017`:

```bash
conda activate kpi
cd backend
python main.py
```

Frontend tại cổng `5191`:

```bash
cd frontend
npm install
npm run dev
```

- API docs: <http://localhost:8017/docs>
- Frontend: <http://localhost:5191>

## Chạy bằng Docker Compose

```bash
cp .env.docker.example .env.docker
# Cập nhật mật khẩu, JWT secret và API key trong .env.docker.
docker compose --env-file .env.docker build --pull
docker compose --env-file .env.docker up -d
```

Với database mới, cần import dữ liệu chính thức và tạo admin một lần theo
[hướng dẫn triển khai Docker](DOCKER.md#4-khởi-tạo-lần-đầu).

## Cấu hình AI

```dotenv
OPENAI_API_KEY=your-openrouter-key
OPENAI_MODEL=openai/gpt-4o-mini
OPENAI_BASE_URL=https://openrouter.ai/api/v1
```

Không có API key, hệ thống dùng client fallback và không tạo số liệu nghiệp vụ
giả. Đặt `USE_REAL_EMBEDDINGS=true` để dùng `BAAI/bge-m3`; mặc định dùng
embedding xác định 1024 chiều để kiểm thử nhanh.

## Kiểm tra PostgreSQL

```bash
psql "$DATABASE_URL"
```

```sql
SELECT unit_type, COUNT(*) FROM departments GROUP BY unit_type;
SELECT organization_role, is_kpi_eligible, COUNT(*) FROM users
GROUP BY 1, 2 ORDER BY 1;
SELECT COUNT(*) FROM work_catalog_items;
SELECT COUNT(*) FROM user_work_areas;
SELECT COUNT(*) FROM tasks;
```
