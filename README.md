# 🤖 Google Form Auto Filler

Tự động điền Google Form nhiều lần theo tỉ lệ cài đặt sẵn.

---

## 📦 Cài đặt

### 1. Yêu cầu
- Python 3.8+
- Google Chrome đã cài đặt
- ChromeDriver (tự động qua `webdriver-manager`)

### 2. Cài thư viện

```bash
pip install -r requirements.txt
```

---

## 🚀 Chạy

```bash
python main.py
```

---

## 🖥️ Demo luồng sử dụng

```
╔══════════════════════════════════════════════════════╗
║         🤖  GOOGLE FORM AUTO FILLER  🤖              ║
╚══════════════════════════════════════════════════════╝

🔗 Nhập URL Google Form: https://docs.google.com/forms/d/e/xxx/viewform

⏳ Đang phân tích form...
✅ Tìm thấy 4 câu hỏi (4 loại được hỗ trợ)

⚙️  CÀI ĐẶT TỈ LỆ CÂU TRẢ LỜI

📌 Câu 1: Bạn đánh giá sản phẩm như thế nào?
   Loại: multiple_choice
   Các lựa chọn:
     [1] Rất tốt
     [2] Tốt
     [3] Bình thường
     [4] Kém

  Nhập tỉ lệ: 30 40 20 10
  ✅ Tỉ lệ: Rất tốt: 30.0% | Tốt: 40.0% | Bình thường: 20.0% | Kém: 10.0%

...

🚀 CÀI ĐẶT CHẠY
Số lần submit: 100
Delay ngẫu nhiên (giây): 2 5

🚀 ĐANG CHẠY...
  [   1/100] ✅ OK  → chờ 3.2s
  [   2/100] ✅ OK  → chờ 4.7s
  ...

📊 BÁO CÁO KẾT QUẢ
  Tổng submit     : 100
  ✅ Thành công   : 100  (100.0%)
  ❌ Thất bại     : 0    (0.0%)
  ⏱️  Thời gian    : 6 phút 23 giây
  ⚡ Trung bình/lần: 3.83 giây

📈 PHÂN PHỐI CÂU TRẢ LỜI THỰC TẾ

  ❓ Bạn đánh giá sản phẩm như thế nào?
    Rất tốt                             32   32.0%  (mục tiêu: 30%)  ██████
    Tốt                                 38   38.0%  (mục tiêu: 40%)  ███████
    Bình thường                         19   19.0%  (mục tiêu: 20%)  ███
    Kém                                 11   11.0%  (mục tiêu: 10%)  ██
```

---

## 📂 Cấu trúc project

```
google_form_filler/
├── main.py          # Entry point
├── parser.py        # Phân tích cấu trúc form (Selenium headless)
├── config.py        # Terminal UI cài đặt tỉ lệ
├── submitter.py     # Submit form qua HTTP POST
├── reporter.py      # Báo cáo kết quả
└── requirements.txt
```

---

## ✅ Loại câu hỏi hỗ trợ

| Loại | Mô tả |
|------|-------|
| `multiple_choice` | Chọn một (radio button) |
| `checkbox` | Chọn nhiều (checkbox) |
| `dropdown` | Menu thả xuống |
| `linear_scale` | Thang điểm 1-5, 1-10... |
| `short_text` | Văn bản ngắn |
| `paragraph` | Đoạn văn dài |
| `date` | Ngày tháng |
| `time` | Giờ giấc |

---

## ⚠️ Lưu ý

- Form phải **công khai** (không yêu cầu đăng nhập Google)
- Chỉ dùng cho form của **chính bạn** hoặc có sự cho phép
- Delay ngẫu nhiên giúp tránh bị chặn rate limit
- Tool dùng cho mục đích nghiên cứu, khảo sát nội bộ
