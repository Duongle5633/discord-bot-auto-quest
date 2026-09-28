# Hướng Dẫn Sử Dụng Tool Treo Voice Discord 24/7 (`treo_voice.py`)

Công cụ Python độc lập giúp tài khoản Discord tự động đăng nhập bằng **User Token**, nhận **ID Kênh Voice** và treo trong phòng voice 24/7 liên tục.

---

## 🚀 Các Tính Năng Nổi Bật

- **Nhập ID Kênh Voice trực tiếp**: Dán ID là vào thẳng kênh voice, không cần mất công tìm kiếm qua từng server.
- **Duyệt danh sách trực quan**: Nếu không nhớ ID, script tự hiển thị danh sách Server và các Kênh Voice để bạn chọn bằng số thứ tự.
- **Tự động kết nối lại (Anti-Kick & Anti-AFK)**:
  - Nếu bị rớt mạng hoặc bị ai đó ngắt kết nối: Tự động kết nối lại sau 5 giây.
  - Nếu bị chuyển sang phòng AFK của Server: Tự động nhận diện và nhảy ngược lại phòng voice đã chọn.
- **Tự tắt Mic & Tai nghe (Self-Mute / Self-Deafen)**: Tiết kiệm băng thông, không phát âm thanh, hiển thị biểu tượng tắt tai nghe trên Discord.
- **Đồng hồ đo thời gian (Uptime Monitor)**: Đếm thời gian bạn đã treo (Ví dụ: `01 giờ 45 phút 10 giây`), hiển thị Ping kết nối.
- **Ghi nhớ cấu hình tự động**: Lưu vào file `voice_config.json`, những lần chạy sau chỉ cần mở lên là tự vào mà không cần nhập lại.

---

## 📋 Bước 1: Cách Lấy Token và ID Kênh Voice

### 1. Cách Lấy User Token
1. Mở Discord trên trình duyệt web (Chrome, Edge, Cốc Cốc, Brave...) hoặc Discord Desktop.
2. Bấm phím **F12** (hoặc `Ctrl + Shift + I`) để mở mục **Developer Tools (Công cụ dành cho nhà phát triển)**.
3. Chọn tab **Console**, dán đoạn code sau vào và nhấn **Enter**:
   ```javascript
   window.webpackChunkdiscord_app.push([
     [Math.random()],
     {},
     (req) => {
       for (const m of Object.keys(req.c).map((x) => req.c[x].exports).filter((x) => x)) {
         if (m.default && m.default.getToken !== undefined) {
           return console.log('%cTOKEN CỦA BẠN: ' + m.default.getToken(), 'color: #00ff00; font-size: 16px;');
         }
         if (m.getToken !== undefined) {
           return console.log('%cTOKEN CỦA BẠN: ' + m.getToken(), 'color: #00ff00; font-size: 16px;');
         }
       }
     }
   ]);
   ```
4. Copy chuỗi Token hiện ra (dạng chuỗi ký tự dài).

---

### 2. Cách Lấy ID Kênh Voice
1. Trên Discord, vào **Cài đặt người dùng (User Settings)** -> **Nâng cao (Advanced)**.
2. Bật công tắc **Chế độ nhà phát triển (Developer Mode)** lên.
3. Vào Server và tìm Kênh Voice bạn muốn treo:
   - **Chuột phải** vào tên Kênh Voice.
   - Chọn **Sao chép ID Kênh (Copy Channel ID)**.

---

## 💻 Bước 2: Cách Chạy Tool

Mở Terminal / PowerShell trong thư mục này và dùng một trong các cách sau:

### Cách 1: Chạy tương tác (Khuyên dùng)
```bash
python treo_voice.py
```
- Tool sẽ hỏi bạn:
  1. **Nhập Token**: Dán Token tài khoản của bạn (hoặc chọn từ danh sách nếu đã từng lưu).
  2. **Nhập ID Kênh Voice**: Dán trực tiếp ID Kênh Voice bạn vừa copy vào.
  3. Chọn **Tự tắt Mic (Mute)** và **Tự tắt Tai nghe (Deafen)** (nhấn Enter để mặc định là BẬT).
  4. Chọn lưu cấu hình để lần sau tự vào.

---

### Cách 2: Chạy nhanh bằng 1 dòng lệnh duy nhất
Nếu bạn đã có sẵn Token và ID Kênh Voice, bạn có thể chạy thẳng không cần qua bất kỳ câu hỏi nào:
```bash
python treo_voice.py --token "NHẬP_TOKEN_Ở_ĐÂY" --channel NHẬP_ID_VOICE_Ở_ĐÂY
```

*Ví dụ:*
```bash
python treo_voice.py --token "MTIxOTM4NDc5..." --channel 1259347354423922710
```

---

### Cách 3: Đổi Kênh Voice hoặc Chọn Lại từ Đầu
Khi bạn muốn chuyển sang kênh voice khác hoặc đổi token:
```bash
python treo_voice.py --setup
```

---

## ⚙️ Bảng Tùy Chọn Dòng Lệnh (CLI Options)

| Tham số | Ý nghĩa | Ví dụ |
| :--- | :--- | :--- |
| `--token` | Truyền mã Token trực tiếp | `--token "MTIz..."` |
| `--channel` | Truyền ID Kênh Voice trực tiếp | `--channel 123456789012345678` |
| `--mute` | Bật/tắt tự tắt micro (`true` hoặc `false`) | `--mute true` |
| `--deaf` | Bật/tắt tự tắt tai nghe (`true` hoặc `false`) | `--deaf true` |
| `--status` | Cài đặt nội dung trạng thái hiển thị | `--status "Đang nghe nhạc chill"` |
| `--setup` | Mở lại giao diện cài đặt để chọn lại Server/Kênh | `--setup` |
| `--help` | Xem danh sách các tham số | `--help` |

---

## 🛑 Cách Dừng Treo Voice
Khi bạn muốn thoát:
- Nhấn tổ hợp phím **`Ctrl + C`** trên cửa sổ dòng lệnh.
- Tool sẽ tự động ngắt kết nối an toàn khỏi kênh voice, in tổng thời gian bạn đã treo và đóng ứng dụng.
