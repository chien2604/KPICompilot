# Triển khai Docker - AI KPI Copilot UBND xã Nghĩa Lâm

Hệ thống được đóng gói thành ba service:

| Service | Image | Cổng host mặc định | Dữ liệu bền vững |
| --- | --- | --- | --- |
| `frontend` | React build + Nginx | `5191` | Không |
| `backend` | FastAPI + AI/GraphRAG | `127.0.0.1:8017` | `backend_storage` |
| `postgres` | PostgreSQL 16 + pgvector | `127.0.0.1:5433` | `postgres_data` |

Nginx chuyển tiếp mọi request `/api/*` tới backend qua mạng Docker nội bộ. Vì
vậy trình duyệt chỉ cần truy cập cổng frontend và không cần biết địa chỉ backend.

## 1. Yêu cầu máy chủ

- Linux 64-bit, khuyến nghị Ubuntu 22.04/24.04.
- RAM tối thiểu 4 GB; khuyến nghị 8 GB nếu bật embedding thật.
- Docker Engine 24+ và Docker Compose plugin 2.20+.
- Git.
- Mở cổng TCP `5191` trên firewall/security group.

Kiểm tra:

```bash
docker --version
docker compose version
git --version
```

## 2. Chuẩn bị biến môi trường

Tại thư mục gốc repository:

```bash
cp .env.docker.example .env.docker
openssl rand -hex 32
nano .env.docker
```

Thay tối thiểu các biến sau:

```dotenv
POSTGRES_PASSWORD=mat_khau_postgres_dai_va_ngau_nhien
JWT_SECRET_KEY=chuoi_64_ky_tu_vua_tao
BOOTSTRAP_ADMIN_EMAIL=admin@example.gov.vn
BOOTSTRAP_ADMIN_PASSWORD=mat_khau_admin_manh
```

Nếu dùng OpenRouter/OpenAI, khai báo thêm:

```dotenv
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=openai/gpt-4o-mini
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_SITE_URL=http://IP_SERVER:5191
CORS_ORIGINS=http://IP_SERVER:5191
```

Không commit `.env.docker`; file này đã được đưa vào `.gitignore`. Mật khẩu
PostgreSQL nên chỉ dùng chữ, số và dấu gạch dưới vì nó được ghép vào connection
URL của backend.

Kiểm tra YAML và biến môi trường trước khi chạy:

```bash
docker compose --env-file .env.docker config --quiet
```

## 3. Build image

```bash
docker compose --env-file .env.docker build --pull
```

Backend image chứa hai workbook chính thức dưới tên ổn định:

- `/app/import-data/personnel.xlsx`
- `/app/import-data/work-catalog.xlsx`

Không có `.env`, API key hoặc mật khẩu nào được copy vào image.

## 4. Khởi tạo lần đầu

Chỉ dùng phần này khi database mới hoàn toàn.

Khởi động PostgreSQL:

```bash
docker compose --env-file .env.docker up -d postgres
```

Import 42 cán bộ, cơ cấu đơn vị, tiêu chí KPI và danh mục công việc:

```bash
docker compose --env-file .env.docker run --rm backend \
  python scripts/import_personnel.py
```

Tạo tài khoản quản trị từ `BOOTSTRAP_ADMIN_*` trong `.env.docker`:

```bash
docker compose --env-file .env.docker run --rm backend \
  python scripts/create_admin.py
```

Khởi động toàn bộ hệ thống:

```bash
docker compose --env-file .env.docker up -d
docker compose --env-file .env.docker ps
```

Truy cập:

- Ứng dụng: `http://IP_SERVER:5191`
- Backend health trên chính server: `http://127.0.0.1:8017/health`
- Swagger trên chính server: `http://127.0.0.1:8017/docs`

Backend tự chờ PostgreSQL, tạo extension `vector`, tạo schema và chạy toàn bộ
migration mỗi lần container khởi động. Các thao tác này có thể chạy lặp an toàn.

> Không chạy lại `scripts/import_personnel.py` trên hệ thống đang có dữ liệu nếu
> chưa sao lưu. Script này chủ động reset nhiệm vụ, minh chứng, KPI, báo cáo và
> hội thoại trước khi nhập lại nguồn chính thức.

## 5. Kiểm tra sau triển khai

```bash
curl --fail http://localhost:5191/nginx-health
curl --fail http://127.0.0.1:8017/health
docker compose --env-file .env.docker ps
docker compose --env-file .env.docker logs --tail=100 backend
```

Đăng nhập bằng tài khoản `BOOTSTRAP_ADMIN_EMAIL` và kiểm tra các màn Tổng quan,
Heatmap, Hồ sơ, Công việc, Minh chứng, AI đánh giá, AI Copilot và Báo cáo.

## 6. Cập nhật phiên bản trên server

Không import lại dữ liệu khi cập nhật code thông thường:

```bash
git pull --ff-only
docker compose --env-file .env.docker build --pull
docker compose --env-file .env.docker up -d --remove-orphans
docker image prune -f
```

Theo dõi quá trình migration và khởi động:

```bash
docker compose --env-file .env.docker logs -f backend
```

Nhấn `Ctrl+C` chỉ thoát màn hình log, không dừng container.

## 7. Dừng và khởi động lại

```bash
docker compose --env-file .env.docker stop
docker compose --env-file .env.docker start
docker compose --env-file .env.docker restart backend
```

Dừng và xóa container/network nhưng giữ database, uploads và KuzuDB:

```bash
docker compose --env-file .env.docker down
```

Không dùng `docker compose down -v` trên production vì tùy chọn `-v` xóa cả
PostgreSQL và kho dữ liệu backend.

## 8. Sao lưu

Tạo thư mục backup và sao lưu PostgreSQL:

```bash
mkdir -p backups
docker compose --env-file .env.docker exec -T postgres \
  sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
  > backups/kpi_government.dump
```

Sao lưu uploads và KuzuDB:

```bash
docker run --rm \
  -v nghia-lam-kpi_backend_storage:/data:ro \
  -v "$(pwd)/backups:/backup" \
  alpine:3.21 tar -czf /backup/backend_storage.tar.gz -C /data .
```

## 9. Mở backend ra ngoài nếu thật sự cần

Mặc định cổng `8017` và `5433` chỉ bind vào loopback để không công khai API và
database. Nếu cần truy cập Swagger từ máy khác, đổi tạm:

```dotenv
BACKEND_BIND_ADDRESS=0.0.0.0
```

Sau đó chạy lại `docker compose up -d`. Không mở cổng PostgreSQL `5433` ra
Internet. Với domain production, nên đặt HTTPS reverse proxy phía trước cổng
`5191` thay vì công khai thêm backend.

## 10. Xử lý lỗi thường gặp

Xem trạng thái và log:

```bash
docker compose --env-file .env.docker ps
docker compose --env-file .env.docker logs --tail=200 postgres
docker compose --env-file .env.docker logs --tail=200 backend
docker compose --env-file .env.docker logs --tail=200 frontend
```

Kiểm tra cổng đang được sử dụng:

```bash
sudo ss -ltnp | grep -E ':5191|:8017|:5433'
```

Nếu cổng bị chiếm, dừng tiến trình cũ hoặc đổi `FRONTEND_PORT`, `BACKEND_PORT`,
`POSTGRES_PORT` trong `.env.docker` rồi chạy `docker compose up -d` lại.

## 11. Push Git từ máy phát triển

Repository hiện dùng remote `origin`. Trước khi commit, kiểm tra để chắc chắn
không có secret:

```bash
git status
git diff --stat
git check-ignore .env.docker backend/.env frontend/.env
```

Commit toàn bộ phiên bản đã kiểm tra:

```bash
git add -A
git status
git commit -m "feat: package KPI Copilot for Docker deployment"
git push -u origin chien
```

Nếu triển khai từ nhánh khác, thay `chien` bằng tên nhánh đó. Không dùng
`git add -f` cho `.env.docker`, `backend/.env` hoặc `frontend/.env`.

## 12. Clone và chạy trên server

Clone qua HTTPS:

```bash
git clone --branch chien --single-branch \
  https://github.com/chien2604/KPICompilot.git
cd KPICompilot
```

Hoặc clone repository riêng tư qua SSH:

```bash
git clone --branch chien --single-branch \
  git@github.com:chien2604/KPICompilot.git
cd KPICompilot
```

Sau đó thực hiện lần lượt:

```bash
cp .env.docker.example .env.docker
nano .env.docker
docker compose --env-file .env.docker config --quiet
docker compose --env-file .env.docker build --pull
docker compose --env-file .env.docker up -d postgres
docker compose --env-file .env.docker run --rm backend \
  python scripts/import_personnel.py
docker compose --env-file .env.docker run --rm backend \
  python scripts/create_admin.py
docker compose --env-file .env.docker up -d
docker compose --env-file .env.docker ps
```

Mở firewall Ubuntu nếu đang bật UFW:

```bash
sudo ufw allow 5191/tcp
sudo ufw status
```

Ứng dụng sẵn sàng tại `http://IP_SERVER:5191`.
