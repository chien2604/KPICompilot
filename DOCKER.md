# Triển khai Docker - AI KPI Copilot UBND xã Nghĩa Lâm

Hệ thống được đóng gói thành bốn service. Docker Nginx là điểm public duy nhất:

| Service | Vai trò | Kết nối |
| --- | --- | --- |
| `nginx` | Gateway HTTPS duy nhất | Host `80/443` → container `80/443` |
| `frontend` | React build + Nginx nội bộ | `frontend:80` |
| `backend` | FastAPI + AI/GraphRAG nội bộ | `backend:8017` |
| `postgres` | PostgreSQL 16 + pgvector nội bộ | `postgres:5432` |

Nginx chuyển `/` tới frontend và giữ nguyên `/api` khi chuyển request tới backend.
Frontend, backend và PostgreSQL không publish cổng trực tiếp lên host.

## 1. Yêu cầu máy chủ

- Linux 64-bit, khuyến nghị Ubuntu 22.04/24.04.
- RAM tối thiểu 4 GB; khuyến nghị 8 GB nếu bật embedding thật.
- Docker Engine 24+ và Docker Compose plugin 2.20+.
- Git.
- Domain đã có bản ghi DNS `A`/`AAAA` trỏ về IP public của server.
- Chứng chỉ TLS hợp lệ cho domain; có thể dùng Let's Encrypt trên host.
- Host cho phép kết nối TCP vào cổng `80` và `443`.

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
# Hai đường dẫn này nằm trên host và được mount read-only vào Nginx.
# Ví dụ Let's Encrypt:
# /etc/letsencrypt/live/kpi.example.gov.vn/fullchain.pem
# /etc/letsencrypt/live/kpi.example.gov.vn/privkey.pem
SSL_CERTIFICATE_PATH=/duong/dan/toi/fullchain.pem
SSL_CERTIFICATE_KEY_PATH=/duong/dan/toi/privkey.pem
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
OPENROUTER_SITE_URL=https://kpi.example.gov.vn
CORS_ORIGINS=https://kpi.example.gov.vn
```

Không commit `.env.docker`; file này đã được đưa vào `.gitignore`. Mật khẩu
PostgreSQL nên chỉ dùng chữ, số và dấu gạch dưới vì nó được ghép vào connection
URL của backend.

Mở [`nginx/default.conf`](nginx/default.conf) và thay cả hai dòng
`server_name localhost;` bằng domain thật. Ví dụ:

```nginx
server_name kpi.example.gov.vn;
```

Hai việc phải tự cấu hình theo server thực tế là domain và đường dẫn chứng chỉ.
Không commit private key vào Git.

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

Truy cập sau khi DNS và TLS đã cấu hình:

- Ứng dụng: `https://kpi.example.gov.vn`
- API: `https://kpi.example.gov.vn/api/...`
- Backend và Swagger không được publish trực tiếp; truy cập nội bộ qua Docker
  network khi cần vận hành.

Backend tự chờ PostgreSQL, tạo extension `vector`, tạo schema và chạy toàn bộ
migration mỗi lần container khởi động. Các thao tác này có thể chạy lặp an toàn.

> Không chạy lại `scripts/import_personnel.py` trên hệ thống đang có dữ liệu nếu
> chưa sao lưu. Script này chủ động reset nhiệm vụ, minh chứng, KPI, báo cáo và
> hội thoại trước khi nhập lại nguồn chính thức.

## 5. Kiểm tra sau triển khai

```bash
curl -I http://localhost
curl -Ik https://localhost
curl -ik https://localhost/api/auth/me
docker compose --env-file .env.docker ps
docker compose --env-file .env.docker logs --tail=100 backend
docker compose --env-file .env.docker logs --tail=100 nginx
```

HTTP phải trả redirect `301` sang HTTPS. Request `/api/auth/me` trả
`401 Unauthorized` khi không có token là kết quả mong đợi và xác nhận gateway đã
chuyển nguyên đường dẫn `/api` tới FastAPI.

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

## 9. Cấu hình domain và SSL

Docker Nginx public trực tiếp cổng `80/443`; không cần reverse proxy khác trên
host. Trước khi khởi động, tự thực hiện hai cấu hình sau theo server:

1. Trỏ DNS của domain về IP public server và thay hai dòng `server_name` trong
   `nginx/default.conf`.
2. Cấp chứng chỉ TLS, sau đó khai báo đường dẫn host trong `.env.docker` qua
   `SSL_CERTIFICATE_PATH` và `SSL_CERTIFICATE_KEY_PATH`.

Ví dụ khi Certbot đã tạo chứng chỉ trên host:

```dotenv
SSL_CERTIFICATE_PATH=/etc/letsencrypt/live/kpi.example.gov.vn/fullchain.pem
SSL_CERTIFICATE_KEY_PATH=/etc/letsencrypt/live/kpi.example.gov.vn/privkey.pem
```

Các file được mount read-only vào container. Khi Certbot gia hạn chứng chỉ, tạo
lại riêng container Nginx để chắc chắn nhận đúng file certificate mới:

```bash
docker compose --env-file .env.docker up -d --force-recreate nginx
```

## 10. Xử lý lỗi thường gặp

Xem trạng thái và log:

```bash
docker compose --env-file .env.docker ps
docker compose --env-file .env.docker logs --tail=200 postgres
docker compose --env-file .env.docker logs --tail=200 backend
docker compose --env-file .env.docker logs --tail=200 frontend
docker compose --env-file .env.docker logs --tail=200 nginx
```

Kiểm tra cổng đang được sử dụng:

```bash
sudo ss -ltnp | grep -E ':(80|443)\b'
```

Nếu cổng `80` hoặc `443` bị chiếm, xác định và dừng reverse proxy/container cũ
trước khi chạy Compose. Không đổi sang cổng khác nếu server cần public HTTP/HTTPS
chuẩn. Các biến cũ `PUBLIC_PORT`, `FRONTEND_PORT`, `BACKEND_PORT`,
`POSTGRES_PORT` và `*_BIND_ADDRESS` không còn được sử dụng.

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

Mở HTTP/HTTPS trên firewall nếu UFW đang bật:

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

Sau khi DNS và chứng chỉ hợp lệ, kiểm tra `https://DOMAIN` và endpoint thực tế
`https://DOMAIN/api/auth/me` như mục 5.
