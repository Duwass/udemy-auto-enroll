# 🎓 Udemy Auto-Enroll Tool

Tự động đăng ký các khóa học Udemy miễn phí từ bài viết Facebook. Hỗ trợ hàng đợi (queue), tự động scan khóa học, và tự khôi phục khi mất mạng.

## ⚡ Quick Start

### 1. Cài đặt dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Đăng nhập tài khoản (chỉ cần 1 lần)

Bạn cần đăng nhập cả Udemy và Facebook để tool có thể hoạt động:

```bash
# Đăng nhập Udemy (để đăng ký khóa học)
python main.py login

# Đăng nhập Facebook (để quét link từ các group/bài viết đóng)
python main.py login-fb
```

Browser sẽ mở ra → Đăng nhập tài khoản tương ứng → Nhấn Enter trong terminal. Session sẽ được lưu lại vĩnh viễn.

### 3. Paste link và đăng ký (cách nhanh nhất)

```bash
python main.py watch
```

Terminal sẽ chờ bạn paste link Facebook. Chỉ cần paste → tự động thêm vào queue:

```
📋 Paste link: https://www.facebook.com/share/p/abc123/
✓ Đã thêm: FB Coupons #1 (10/03/2026) (ID: 29)

📋 Paste link: run    ← gõ 'run' để chạy queue
📋 Paste link: list   ← gõ 'list' để xem queue
📋 Paste link: exit   ← gõ 'exit' để thoát
```

Hoặc double-click file **`start.bat`** để vào chế độ paste link ngay.

### 4. Hàng đợi (Queue)

```bash
# Thêm link (tên tự động theo ngày + thứ tự)
python main.py queue add "https://facebook.com/post1"

# Hoặc thêm với tên tùy chỉnh
python main.py queue add "https://facebook.com/post2" --name "Khóa Excel 05/03"

# Xem hàng đợi
python main.py queue list

# Chạy tất cả links đang chờ (pending)
python main.py queue run

# Chạy riêng 1 hoặc nhiều link theo ID
python main.py queue run 1
python main.py queue run 1 2 5

# Chạy lại các link bị lỗi
python main.py queue run --retry

# Xem danh sách khóa học trong 1 link (sau khi scan)
python main.py queue courses 5

# Xem kết quả
python main.py queue report --latest
```

Khi chạy `queue run`, tool sẽ tự động thực hiện:
1. **Pre-flight Check**: Kiểm tra tự động xem đã đăng nhập đủ Udemy và Facebook chưa.
2. **Phase 1 (Scan)**: Quét tất cả links Facebook để lấy danh sách khóa học (dùng dữ liệu session Facebook).
3. **Phase 2 (Enroll)**: Đăng ký từng khóa học tự động vào tài khoản Udemy của bạn.

> **Mất mạng?** Tool tự động chờ internet khôi phục và tiếp tục từ khóa bị lỗi.

## 📋 Commands

| Lệnh | Mô tả |
|------|-------|
| `python main.py watch` | Chế độ tương tác - paste link |
| `python main.py login` | Đăng nhập Udemy |
| `python main.py login-fb` | Đăng nhập Facebook |
| `python main.py enroll <URL>` | Đăng ký từ 1 bài viết |
| `python main.py history` | Xem lịch sử đăng ký |
| `python main.py status` | Kiểm tra trạng thái đăng nhập |
| `python main.py queue add <URL>` | Thêm link (tên tự động) |
| `python main.py queue list` | Xem hàng đợi |
| `python main.py queue remove <ID>` | Xóa link khỏi hàng đợi |
| `python main.py queue run` | Chạy tất cả links chờ xử lý |
| `python main.py queue run <ID>` | Chạy links theo ID cụ thể |
| `python main.py queue run --retry` | Chạy lại các link bị lỗi |
| `python main.py queue courses <ID>` | Xem khóa học + trạng thái |
| `python main.py queue report` | Xem report kết quả |
| `python main.py queue clear` | Xóa toàn bộ hàng đợi |

## 📁 Cấu trúc

```
├── main.py              # CLI entry point
├── config.py            # Cấu hình
├── start.bat            # Double-click để vào chế độ paste link
├── requirements.txt     # Dependencies
├── data/
│   ├── history.db       # Lịch sử đăng ký (SQLite)
│   ├── queue.json       # Hàng đợi links + courses
│   ├── reports/         # Report kết quả (TXT)
│   ├── browser_data/    # Session Udemy
│   └── fb_browser_data/ # Session Facebook
└── modules/
    ├── facebook_scraper.py   # Đọc Facebook post
    ├── udemy_parser.py       # Parse Udemy URLs
    ├── udemy_enroller.py     # Đăng ký khóa học
    ├── history.py            # Lưu lịch sử
    ├── queue_manager.py      # Quản lý hàng đợi
    ├── report_generator.py   # Tạo report TXT
    └── network.py            # Xử lý mất mạng/retry
```

## 💡 Tips

- **Session lưu vĩnh viễn**: Chỉ cần đăng nhập Udemy và Facebook 1 lần (dữ liệu lưu riêng biệt).
- **Không trùng lặp**: Tool tự bỏ qua khóa đã đăng ký
- **Headless mode**: Đổi `HEADLESS = True` trong `config.py` để chạy ẩn browser
- **Queue**: Thêm nhiều links, chạy 1 lần, xem report sau
- **Network resilience**: Tự chờ nếu mất mạng, tiếp tục khi có internet
- **queue courses**: Xem chi tiết từng khóa với trạng thái (✓ Miễn phí / ⚠ Đã đăng ký / 💰 Mất phí / ✗ Lỗi)

## ⚠️ Lưu ý

- Coupon có thể hết hạn, tool sẽ thông báo nếu không đăng ký được
- Nếu mất mạng giữa chừng, tool sẽ tự động chờ và retry
