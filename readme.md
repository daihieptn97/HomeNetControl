# 🍓 Pi Network Manager

Ứng dụng Python quản lý thiết bị và mạng nội bộ chạy trên **Raspberry Pi 3B**, có giao diện web admin truy cập từ xa qua **Cloudflare Tunnel**.

---

## ✨ Tính năng

**Trang Login**
Màn hình đăng nhập bảo vệ toàn bộ hệ thống. Chỉ admin có tài khoản mới truy cập được vào dashboard quản trị.

**Dashboard Admin**
Màn hình tổng quan sau khi đăng nhập — hiển thị nhanh số thiết bị đang kết nối, trạng thái mạng, cảnh báo mới nhất và các thông số hệ thống Pi.

**Quản lý thiết bị mạng**
Quét và liệt kê tất cả thiết bị đang kết nối vào mạng nội bộ theo thời gian thực. Hiển thị IP, MAC address, hostname, nhà sản xuất. Hỗ trợ đặt tên và ghi chú cho từng thiết bị. Lưu các subnet Pi đã từng kết nối và cho phép quét lại thiết bị trong từng subnet đó.

**Thông tin Pi**
Màn hình riêng để xem hostname, nền tảng, uptime, CPU, nhiệt độ, RAM, swap, ổ đĩa, interface mạng, subnet và địa chỉ IP hiện tại của Raspberry Pi.

**Truy cập Router 192.168.1.1**
Tích hợp giao diện đọc thông tin từ router tại địa chỉ `192.168.1.1`. Lấy thêm dữ liệu mạng như danh sách DHCP leases, cấu hình DNS, trạng thái WAN/LAN, uptime router và các thiết lập nâng cao khác mà ứng dụng không tự thu thập được.

**Thông tin WiFi**
Xem SSID, cường độ tín hiệu, kênh phát, băng tần, subnet và các thông số mạng WiFi cục bộ. Hỗ trợ quét WiFi xung quanh Pi và kết nối tới SSID đã quét bằng mật khẩu do admin nhập.

**Theo dõi băng thông**
Thống kê traffic upload/download theo thiết bị và theo thời gian. Biểu đồ trực quan theo giờ/ngày/tuần.

**Cảnh báo thiết bị lạ**
Tự động phát hiện và thông báo khi có thiết bị chưa từng xuất hiện kết nối vào mạng.

**Màn hình cài đặt**
Tự động kiểm tra các system tools cần thiết. Hiển thị trạng thái từng tool và cài đặt ngay từ giao diện web nếu còn thiếu. Cho phép cấu hình thêm thông tin kết nối router, tài khoản router để lấy dữ liệu sâu hơn.

**Truy cập từ xa**
Web UI chạy trên Pi, expose ra internet an toàn qua Cloudflare Tunnel — không cần mở port trên router.

---

## 🖥️ Luồng giao diện

```
[Trang Login]
     ↓ đăng nhập thành công
[Dashboard Admin]
     ├── Thiết bị mạng
     ├── Thông tin WiFi
     ├── Băng thông
     ├── Router 192.168.1.1   ← lấy thêm dữ liệu từ router
     ├── Cảnh báo
     └── Cài đặt
```

---

## 🛠️ Công nghệ sử dụng

**Backend**

| Công nghệ | Vai trò |
|---|---|
| Python 3.9+ | Ngôn ngữ chính |
| Flask | Web framework, REST API |
| Flask-SocketIO | Real-time cập nhật dữ liệu qua WebSocket |
| Flask-Login | Xác thực, quản lý phiên đăng nhập |
| Scapy | Quét mạng cấp thấp, phân tích packet |
| python-nmap | Wrapper cho nmap, quét thiết bị |
| requests | Gọi API router tại 192.168.1.1 |
| psutil | Đọc thông tin hệ thống, network stats |
| PyYAML | Đọc/ghi file cấu hình |
| schedule | Lập lịch quét mạng định kỳ |

**System Tools (Linux)**

| Tool | Vai trò |
|---|---|
| `nmap` | Quét thiết bị và port trong mạng |
| `arp-scan` | Quét ARP nhanh, phát hiện thiết bị |
| `iw` / `iwconfig` | Đọc thông tin WiFi interface |
| `nmcli` | Quét và kết nối WiFi từ giao diện web |
| `net-tools` | `ifconfig`, `arp`, thông tin mạng |
| `vnstat` | Thống kê băng thông theo thời gian |
| `iptables` | Block/unblock thiết bị theo MAC/IP |
| `curl` | Gọi HTTP tới router 192.168.1.1 |

**Frontend**

| Công nghệ | Vai trò |
|---|---|
| HTML / CSS / JavaScript | Giao diện web |
| Chart.js | Biểu đồ băng thông, thống kê |
| Socket.IO (client) | Nhận cập nhật real-time từ server |

**Hạ tầng**

| Công nghệ | Vai trò |
|---|---|
| Raspberry Pi 3B | Phần cứng chạy ứng dụng |
| Raspberry Pi OS | Hệ điều hành (Bullseye / Bookworm) |
| Cloudflare Tunnel (`cloudflared`) | Expose web UI ra internet không cần mở port |
| systemd | Quản lý service, tự khởi động khi Pi boot |

---

## 🚀 Chạy local/dev

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

Chỉnh `.env` trước khi expose qua Cloudflare Tunnel:

```env
FLASK_SECRET_KEY=change-me-before-cloudflare
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change-me
ROUTER_URL=http://192.168.1.1
MOCK_DATA=true
```

Khởi động web UI:

```bash
.venv/bin/python run.py
```

Mở `http://127.0.0.1:5000`, đăng nhập bằng tài khoản trong `.env`.

---

## 🧪 Kiểm thử

```bash
.venv/bin/python -m pytest -q
```

Test bao phủ đăng nhập, API chính, parser `arp-scan`/`nmap`/WiFi, scan fallback, cập nhật thiết bị, router settings và cảnh báo.

---

## ⚙️ Triển khai Raspberry Pi

1. Cài Python 3.9+ và các system tools cần thiết:

```bash
sudo apt update
sudo apt install -y nmap arp-scan iw wireless-tools network-manager net-tools vnstat curl
```

2. Copy repo vào Pi, tạo `.env`, cài dependencies và chạy `run.py`.

3. Có thể dùng service mẫu tại `deploy/homenetcontrol.service`. Sửa `WorkingDirectory`, `EnvironmentFile`, `ExecStart`, `User`, `Group` theo vị trí deploy thực tế rồi bật service:

```bash
sudo cp deploy/homenetcontrol.service /etc/systemd/system/homenetcontrol.service
sudo systemctl daemon-reload
sudo systemctl enable --now homenetcontrol
```

Cloudflare Tunnel không được app tự tạo vì tunnel đã được triển khai riêng.

---

## 📄 License

MIT License — Tự do sử dụng, chỉnh sửa và phân phối.

---

> Developed for Raspberry Pi 3B · Python 3.9+ · Cloudflare Tunnel
