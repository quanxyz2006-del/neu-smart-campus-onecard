# AGENTS.md - Đặc Tả Kỹ Thuật Toàn Diện Hệ Thống NEU Smart Campus One-Card

## 1. VAI TRÒ & MỤC TIÊU HỆ THỐNG
Bạn là một Senior Full-Stack Architect. Nhiệm vụ của bạn là xây dựng hoàn chỉnh ứng dụng Web Demo **"NEU Smart Campus One-Card"** (Tích hợp Thẻ sinh viên/giảng viên thông minh, Quản lý học vụ, Tài chính kế toán, Đóng góp trực tuyến và Dịch vụ gửi xe không tiền mặt tại Đại học Kinh tế Quốc dân - NEU).

Hệ thống kết nối đồng bộ 4 phân hệ cốt lõi trên cơ sở dữ liệu SQLite (`neu_smart_campus.db`) mà không sao chép dữ liệu dư thừa:
- **Module 20 (Accounts, SSO & Authorization):** Quản lý định danh, đăng nhập phân luồng, phân quyền theo vai trò (RBAC) và ủy quyền quản lý tài chính (`FINANCE_MANAGER`).
- **Module 03 (Student Lifecycle & Academic Records):** Quản lý hồ sơ sinh viên, lớp chuyên ngành, trạng thái học vụ và liên kết thẻ vật lý/thẻ số.
- **Module 07 (Finance, Accounting & Smart Parking):** Quản lý danh mục thu chi, biểu phí gửi xe theo khung giờ/vé tháng, ví trả trước (tiền ảo mặc định `50.000 VNĐ`), luồng nạp tiền/đăng ký thẻ tháng qua MB Bank có bước Admin phê duyệt đối soát, và sinh bút toán kế toán.
- **Module 14 (Online Giving & Honor Roll):** Quản lý đóng góp quỹ trường từ giảng viên/sinh viên/cựu người học, tùy chọn ẩn danh/công khai và duyệt hiển thị lên Bảng vinh danh.

### Tech Stack bắt buộc (Đảm bảo ổn định, chạy ngay tại Local & dễ chia sẻ qua GitHub):
- **Backend:** Python 3.9+ với **Flask** (sử dụng `sqlite3` thuần hoặc `SQLAlchemy`). Tự động tạo bảng và nạp dữ liệu mẫu (Seed Data) ngay khi chạy `python app.py` nếu DB chưa có dữ liệu.
- **Frontend:** HTML5, TailwindCSS (nhúng qua CDN), Vanilla JavaScript (Fetch API), Icons (Lucide hoặc FontAwesome CDN).
- **Typography & Theme:** Sử dụng duy nhất font chữ **`Inter`** từ Google Fonts trên toàn bộ các trang. Giao diện **Light Mode** sạch, sáng, hiện đại (Nền `#F8FAFC`, Card `#FFFFFF`, Màu chủ đạo Xanh NEU `#1E3A8A` / `#2563EB`).

---
## Cấu trúc thư mục dự án
neu-smart-campus/
│
├── AGENTS.md                  # File đặc tả kỹ thuật chi tiết để làm việc với AI (Codex/Cursor)
├── README.md                  # Tài liệu hướng dẫn cài đặt, chạy code và kịch bản test cho nhóm
├── .gitignore                 # Chặn đẩy file rác (venv/, __pycache__/, *.db) lên GitHub
├── requirements.txt           # Danh sách toàn bộ thư viện Python cần cài đặt
│
├── app.py                     # File chạy chính (Entry point): Chứa toàn bộ Routes & Controllers
├── database.py                # Khởi tạo bảng SQLite (M03, M07, M14, M20) & Các hàm truy vấn
├── seed.py                    # Nạp sẵn dữ liệu mẫu: Admin, 43 Sinh viên, 6 Giảng viên, Biểu phí
├── utils.py                   # Hàm chuẩn hóa tiếng Việt không dấu, sinh mật khẩu, tạo link VietQR
│
├── static/                    # Chứa tài nguyên tĩnh (nếu cần mở rộng)
│   ├── css/
│   │   └── custom.css         # CSS bổ trợ cho font chữ Inter và hiệu ứng mượt mà
│   └── js/
│       └── main.js            # Xử lý thông báo Toast, Modal nạp tiền, chống bấm đúp (Idempotency)
│
└── templates/                 # Giao diện HTML5 + TailwindCSS (Đồng bộ Light Mode & Font Inter)
    ├── base.html              # Khung giao diện gốc (Header, Footer, Font Inter, Toast Notification)
    ├── gate.html              # Màn hình 1: Cổng xác minh "Bạn có thuộc NEU không?" (/)
    ├── login.html             # Màn hình 2: Đăng nhập phân luồng + Gợi ý nhanh tài khoản Demo (/login)
    ├── portal.html            # Màn hình 3: Cổng Sinh viên & Giảng viên (/portal/dashboard)
    └── admin.html             # Màn hình 4: Cổng Quản trị viên & Duyệt tài chính (/admin/dashboard)
## 2. QUY TẮC NGHIỆP VỤ CỐT LÕI (STRICT BUSINESS RULES)

### 2.1. Cổng Xác Minh Đầu Vào Tại Trang Chủ (`/`)
- Khi mở hệ thống tại `/`, **CHƯA** hiển thị form đăng nhập ngay mà hiện màn hình xác minh trang trọng:
  > **"Bạn có phải là Sinh viên / Giảng viên / Cán bộ thuộc Đại học Kinh tế Quốc dân (NEU) không?"**
- Hiển thị 2 nút hành động rõ ràng:
  1. **"Đúng, tôi thuộc NEU"**: Chuyển hướng sang trang Đăng nhập (`/login`).
  2. **"Không phải"**: Hiển thị thông báo: *"Hiện tại hệ thống chưa cung cấp dịch vụ cho người dùng ngoài trường. Vui lòng quay lại trang trước."* kèm nút **"Quay lại trang trước"**.

### 2.2. Quy Tắc Tài Khoản, Mật Khẩu Tự Động & Phân Luồng Giao Diện
- **Tài khoản Admin tối cao (Super Admin):**
  - Username: `quan2006`
  - Password: `123456`
  - Sau khi đăng nhập: Chuyển thẳng vào giao diện Quản trị (`/admin/dashboard`).
- **Tài khoản Sinh viên & Giảng viên:**
  - **Username:** Chính là `Mã sinh viên` (VD: `11244018`) hoặc `Mã giảng viên` (VD: `GV001`).
  - **Password:** Chính là `Họ và tên` viết liền, không dấu, chữ thường (chuyển `đ/Đ` thành `d`, xóa mọi khoảng trắng). Ví dụ: `"Hoàng Minh Quân"` -> `"hoangminhquan"`.
  - Sau khi đăng nhập: Chuyển vào giao diện Cổng cá nhân (`/portal/dashboard`).
  - **Trường hợp đặc biệt (Phân quyền M20):** Nếu một tài khoản cố định (VD: Giảng viên `GV004` hoặc tài khoản được Admin cấp quyền `FINANCE_MANAGER`) đăng nhập, họ có thêm nút chuyển sang khu vực **Quản lý Dòng tiền & Duyệt giao dịch** (`/admin/finance`).
- **Cơ chế tự động tích hợp khi Admin thêm/sửa User:**
  - Khi Admin thêm mới hoặc sửa tên 1 Sinh viên / Giảng viên trên trang Admin, hệ thống tự động chạy hàm `generate_password_from_name(full_name)` để sinh mật khẩu không dấu viết liền, tự động tạo ví thẻ với số dư mặc định **`50.000 VNĐ`** và hiển thị rõ Username/Password trên bảng quản lý.

---

## 3. CHI TIẾT LUỒNG CHỨC NĂNG BẮT BUỘC

### 3.1. Chức năng phía Sinh viên & Giảng viên (`/portal/dashboard`)
1. **Hồ sơ Học vụ / Giảng dạy & Thông tin Thẻ (M03 & M07):**
   - Hiển thị thông tin cá nhân (Mã số, Họ tên, Ngày sinh, Lớp/Đơn vị, Trạng thái học vụ/công tác).
   - Giảng viên xem thêm bảng kê giờ giảng và thu nhập mẫu (M07). Sinh viên xem thêm trạng thái học phí và điểm học phần liên kết (M03).
   - Hiển thị **Thẻ Thông Minh NEU (Digital Smart Card)** gồm: Mã thẻ, Loại phương tiện (`Xe máy` / `Xe đạp`), Gói gửi xe hiện tại (`Thẻ thường xuyên - Theo lượt` hoặc `Thẻ tháng KTX`), Trạng thái thẻ (`Đang hoạt động`), và **Số dư khả dụng** (Mặc định `50.000đ`).
2. **Luồng Nạp Tiền Vào Thẻ Qua MB Bank (Chờ Admin Duyệt):**
   - Người dùng nhấn vào **"Trạng thái thẻ"** -> Nhấn nút **"Thêm tiền / Nạp tiền"**.
   - Hiển thị **Modal / Trang Thanh Toán** gồm:
     - Ô nhập số tiền muốn nạp (Có các nút chọn nhanh: `20.000đ`, `50.000đ`, `100.000đ`, `200.000đ`).
     - Thông tin chuyển khoản cố định của Admin:
       - **Ngân hàng:** `MB Bank (Ngân hàng Quân đội)`
       - **Số tài khoản:** `0966618840`
       - **Chủ tài khoản:** `HOANG MINH QUAN`
       - **Nội dung chuyển khoản:** `NAPTHE [Username] [SoTien]`
       - Hiển thị ảnh mã QR VietQR tự động theo công thức: `https://img.vietqr.io/image/MB-0966618840-compact2.png?amount={amount}&addInfo=NAPTHE%20{username}&accountName=HOANG%20MINH%20QUAN`
   - Khi nhấn nút **"Xác nhận đã thanh toán"**:
     - Hệ thống tạo giao dịch loại `TOPUP` với trạng thái **`PENDING` (Đang chờ duyệt)**.
     - **Chưa cộng tiền ngay vào ví**, lưu bản ghi vào mục **"Lịch sử giao dịch"** của người dùng và đẩy thông báo sang trang Admin.
3. **Luồng Đăng Ký Thẻ Tháng Gửi Xe (Chờ Admin Duyệt):**
   - Người dùng nhấn vào mục **"Đăng ký thẻ tháng"** -> Nhấn nút **"Xác nhận đăng ký"**.
   - Hiện Form nhập thông tin:
     - Họ và tên (mặc định điền sẵn, cho phép xác nhận lại).
     - Chọn gói vé tháng theo quy định: **Xe đạp tại KTX (`45.000đ/tháng`)** hoặc **Xe máy tại KTX (`70.000đ/tháng`)**.
     - Nhập Biển số xe (nếu là xe máy).
   - Sau khi xác nhận form, hệ thống chuyển sang **Màn hình thanh toán MB Bank (`0966618840` - `MB Bank`)** với đúng số tiền `45.000đ` hoặc `70.000đ` tương tự quy trình nạp tiền.
   - Khi nhấn **"Xác nhận đã thanh toán"**, hệ thống tạo giao dịch loại `MONTHLY_PASS` ở trạng thái **`PENDING` (Đang chờ duyệt)**, lưu vào lịch sử và gửi thông báo sang trang Admin.
4. **Trạm Mô Phỏng Quẹt Thẻ Gửi Xe (Smart Parking Gate Simulator):**
   - Cho phép người dùng bấm thử **"Quẹt thẻ gửi xe"** với 2 tùy chọn khung giờ: **Trước 18h** và **Sau 18h**.
   - Áp dụng đúng biểu phí:
     - Nếu tài khoản đã được duyệt **Thẻ tháng KTX**: Miễn phí lượt quẹt (`0đ`), ghi nhận lịch sử ra/vào.
     - Nếu dùng **Thẻ thường xuyên (Theo lượt)**:
       - **Xe đạp:** Trước 18h trừ `1.000đ/lượt` | Sau 18h trừ `2.000đ/lượt`.
       - **Xe máy:** Trước 18h trừ `2.000đ/lượt` | Sau 18h trừ `4.000đ/lượt`.
       - *(Hiển thị thêm bảng so sánh phí Vãng lai: Xe đạp 2.000đ - 3.000đ, Xe máy 3.000đ - 4.000đ để làm rõ ưu đãi thẻ tích hợp).*
5. **Đóng góp trực tuyến - Giving (M14):**
   - Form quyên góp quỹ học bổng/hỗ trợ gửi xe cho sinh viên, tùy chọn phạm vi công khai (`Công khai đầy đủ`, `Chỉ hiện tên`, `Ẩn danh`) và hiển thị Bảng vinh danh.

### 3.2. Chức năng phía Admin (`quan2006`) & Quản lý Tài chính (`/admin/dashboard`)
1. **Trung tâm Phê duyệt Giao dịch & Thông báo (Transaction Approval Queue):**
   - Hiển thị badge số lượng yêu cầu đang chờ duyệt (`PENDING`) gồm cả **Nạp tiền thẻ** và **Đăng ký thẻ tháng**.
   - Mỗi dòng yêu cầu hiển thị: Thời gian, Mã SV/GV, Họ tên, Loại yêu cầu (`Nạp tiền` / `Đăng ký thẻ tháng`), Số tiền, Nội dung CK.
   - Admin có 2 nút thao tác:
     - **"Xác nhận đã thanh toán (Duyệt)"**:
       - Nếu là `TOPUP`: Cộng chính xác số tiền đó vào số dư ví của người dùng.
       - Nếu là `MONTHLY_PASS`: Nâng cấp trạng thái thẻ của người dùng lên **`Thẻ Tháng KTX`** (Hiệu lực 30 ngày) và cập nhật loại xe/biển số.
       - Chuyển trạng thái giao dịch sang **`APPROVED` (Đã duyệt)** và tự động sinh bản ghi vào bảng `ChungTu_ButToan` (M07).
     - **"Từ chối"**: Chuyển trạng thái sang **`REJECTED` (Từ chối)**, giữ nguyên số dư.
2. **Quản lý Tài khoản Sinh viên & Giảng viên (CRUD + Tích hợp Mật khẩu tự động):**
   - Bảng danh sách có bộ lọc theo Vai trò (`Sinh viên` / `Giảng viên`), Lớp học và ô tìm kiếm theo Mã số / Họ tên.
   - **Thêm mới (Create):** Admin nhập Mã SV/GV, Họ và tên, Ngày sinh, Lớp/Khoa, Vai trò, Loại xe -> Hệ thống tự động tạo tài khoản với `Username = Mã số`, `Password = tên không dấu viết liền chữ thường`, và `Số dư = 50.000đ`.
   - **Sửa (Update):** Sửa Họ tên (tự động cập nhật lại mật khẩu không dấu tương ứng), Lớp/Khoa, Loại xe, Gói thẻ.
   - **Xóa (Delete):** Xóa tài khoản và dữ liệu liên kết.
3. **Thay đổi Số dư Tiền trực tiếp (Admin Balance Control):**
   - Tại mỗi dòng tài khoản Sinh viên / Giảng viên, Admin có nút **"Sửa số tiền"** để nhập số dư mới bất kỳ (hoặc cộng/trừ nhanh) phục vụ kiểm thử và demo.
4. **Phân quyền Quản lý Dòng tiền (M20 Role Assignment):**
   - Admin (`quan2006`) có thể cấp hoặc thu hồi quyền **`FINANCE_MANAGER` (Quản lý tiền ra vào hệ thống)** cho các tài khoản cố định (ví dụ cấp cho các giảng viên `GV001` đến `GV006`).
5. **Nút "Reset Demo Data":**
   - Cho phép khôi phục toàn bộ cơ sở dữ liệu về trạng thái mẫu ban đầu chỉ với 1 click.

---

## 4. DỮ LIỆU MẪU BẮT BUỘC NẠP SẴN VÀO SQLITE (`seed.py`)

Hãy sử dụng chính xác hàm chuẩn hóa tiếng Việt và danh sách dữ liệu dưới đây để nạp vào cơ sở dữ liệu ngay khi khởi chạy:

```python
import unicodedata

def generate_password_from_name(full_name: str) -> str:
    """Chuyển Họ và tên có dấu thành mật khẩu chữ thường, viết liền, không dấu."""
    if not full_name:
        return ""
    s = full_name.replace('đ', 'd').replace('Đ', 'D')
    s = unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode('utf-8')
    return "".join(s.split()).lower()

# 1. TÀI KHOẢN SUPER ADMIN
ADMIN_ACCOUNT = {
    "username": "quan2006",
    "password": "123456",
    "full_name": "Hoàng Minh Quân (Admin)",
    "role": "ADMIN",
    "can_manage_finance": True
}

# 2. DANH SÁCH 43 SINH VIÊN MẪU (40 SV từ file điểm danh CNTT1181(126)_03 + 3 SV nhóm)
# Cấu trúc: (Mã_SV, Họ_và_Tên, Ngày_Sinh, Lớp, Mật_Khẩu_Tự_Động, Số_Dư_Mặc_Định, Loại_Xe)
SEED_STUDENTS = [
    ("11243396", "Phạm Tuấn Anh", "30/12/2006", "66A.HTQL", "phamtuananh", 50000, "Xe máy"),
    ("11243893", "Đào Hoàng Gia Bảo", "06/06/2006", "66C.CNTT", "daohoanggiabao", 50000, "Xe máy"),
    ("11243402", "Tạ Hồng Diệp", "18/12/2006", "66A.HTQL", "tahongdiep", 50000, "Xe đạp"),
    ("11243906", "Lê Thị Diệu", "26/04/2006", "66C.CNTT", "lethidieu", 50000, "Xe đạp"),
    ("11243922", "Trần Khánh Duy", "20/10/2006", "66C.CNTT", "trankhanhduy", 50000, "Xe máy"),
    ("11243914", "Trần Đình Dũng", "27/01/2006", "66C.CNTT", "trandinhdung", 50000, "Xe máy"),
    ("11243411", "Khuất Thùy Dương", "10/08/2006", "66A.HTQL", "khuatthuyduong", 50000, "Xe đạp"),
    ("11243405", "Đinh Anh Đức", "20/11/2006", "66A.HTQL", "dinhanhduc", 50000, "Xe máy"),
    ("11243759", "Nguyễn Ngô Minh Đức", "02/02/2006", "66.KHMT", "nguyenngominhduc", 50000, "Xe máy"),
    ("11243909", "Nguyễn Tuấn Đức", "28/12/2003", "66C.CNTT", "nguyentuanduc", 50000, "Xe máy"),
    ("11246860", "Lê Quang Hà", "27/09/2006", "66C.CNTT", "lequangha", 50000, "Xe máy"),
    ("11243926", "Đặng Nhật Hải", "27/03/2006", "66A.CNTT", "dangnhathai", 50000, "Xe máy"),
    ("11243935", "Nguyễn Minh Hiếu", "05/01/2006", "66C.CNTT", "nguyenminhhieu", 50000, "Xe máy"),
    ("11243941", "Nguyễn Minh Hoàng", "04/08/2006", "66C.CNTT", "nguyenminhhoang", 50000, "Xe máy"),
    ("11243948", "Đinh Quang Huy", "23/06/2006", "66C.CNTT", "dinhquanghuy", 50000, "Xe máy"),
    ("11243950", "Hàn Thị Khánh Huyền", "14/01/2006", "66B.CNTT", "hanthikhanhhuyen", 50000, "Xe đạp"),
    ("11243955", "Phạm Minh Khiêm", "05/04/2006", "66C.CNTT", "phamminhkhiem", 50000, "Xe máy"),
    ("11243958", "Lý Khải Kiên", "28/09/2006", "66C.CNTT", "lykhaikien", 50000, "Xe máy"),
    ("11243432", "Lương Diệu Linh", "09/07/2006", "66A.HTQL", "luongdieulinh", 50000, "Xe đạp"),
    ("11243969", "Nguyễn Thị Khánh Linh", "28/11/2006", "66C.CNTT", "nguyenthikhanhlinh", 50000, "Xe đạp"),
    ("11243981", "Trần Nguyễn Thanh Mai", "25/08/2006", "66C.CNTT", "trannguyenthanhmai", 50000, "Xe đạp"),
    ("11243984", "Nguyễn Duy Mạnh", "03/01/2006", "66C.CNTT", "nguyenduymanh", 50000, "Xe máy"),
    ("11243996", "Nguyễn Khánh Nam", "24/05/2006", "66C.CNTT", "nguyenkhanhnam", 50000, "Xe máy"),
    ("11243998", "Nguyễn Thị Thúy Nga", "18/03/2006", "66C.CNTT", "nguyenthithuynga", 50000, "Xe đạp"),
    ("11243790", "Đỗ Đức Nghĩa", "11/05/2002", "66.KHMT", "doducnghia", 50000, "Xe máy"),
    ("11244003", "Nguyễn Nam Quảng Ngọc", "05/05/2006", "66A.CNTT", "nguyennamquangngoc", 50000, "Xe máy"),
    ("11244018", "Hoàng Minh Quân", "14/02/2006", "66C.CNTT", "hoangminhquan", 50000, "Xe máy"),
    ("11244020", "Sầm Anh Quân", "07/01/2006", "66B.CNTT", "samanhquan", 50000, "Xe máy"),
    ("11244021", "Trần Anh Quân", "09/06/2006", "66C.CNTT", "trananhquan", 50000, "Xe máy"),
    ("11244027", "Nguyễn Xuân Sang", "23/02/2006", "66C.CNTT", "nguyenxuansang", 50000, "Xe máy"),
    ("11244030", "Đặng Xuân Thành", "02/06/2006", "66C.CNTT", "dangxuanthanh", 50000, "Xe máy"),
    ("11244034", "Vũ Tuấn Thịnh", "01/02/2006", "66C.CNTT", "vutuanthinh", 50000, "Xe máy"),
    ("11243478", "Nguyễn Anh Thơ", "17/02/2006", "66A.HTQL", "nguyenanhtho", 50000, "Xe đạp"),
    ("11244040", "Trần Thị Thùy", "01/10/2006", "66C.CNTT", "tranthithuy", 50000, "Xe đạp"),
    ("11243479", "Nguyễn Lý Anh Thư", "14/10/2006", "66A.HTQL", "nguyenlyanhthu", 50000, "Xe đạp"),
    ("11244038", "Phan Anh Thư", "19/02/2006", "66C.CNTT", "phananhthu", 50000, "Xe đạp"),
    ("11243803", "Trương Ngọc Tiến", "17/10/2006", "66.KHMT", "truongngoctien", 50000, "Xe máy"),
    ("11244048", "Nguyễn Thùy Trang", "16/03/2006", "66C.CNTT", "nguyenthuytrang", 50000, "Xe đạp"),
    ("11244051", "Nguyễn Xuân Trường", "29/01/2006", "66A.CNTT", "nguyenxuantruong", 50000, "Xe máy"),
    ("11244052", "Đinh Văn Minh Tuấn", "11/11/2006", "66C.CNTT", "dinhvanminhtuan", 50000, "Xe máy"),
    # 3 Sinh viên nhóm bổ sung
    ("11244019", "Nguyễn Thành Công", "15/05/2006", "66C.CNTT", "nguyenthanhcong", 50000, "Xe máy"),
    ("11244022", "Phùng Quang Đăng", "20/08/2006", "66C.CNTT", "phungquangdang", 50000, "Xe đạp"),
    ("11244023", "Phạm Xuân Thành", "12/11/2006", "66C.CNTT", "phamxuanthanh", 50000, "Xe máy"),
]

# 3. DANH SÁCH 6 GIẢNG VIÊN MẪU
# Cấu trúc: (Mã_GV, Họ_và_Tên, Đơn_Vị, Mật_Khẩu_Tự_Động, Số_Dư_Mặc_Định, Quyền_Quản_Lý_Tài_Chính)
SEED_LECTURERS = [
    ("GV001", "Phạm Xuân Lâm", "Viện CNTT & KTS", "phamxuanlam", 50000, False),
    ("GV002", "Cao Thu Hương", "Viện CNTT & KTS", "caothuhuong", 50000, False),
    ("GV003", "Đặng Minh Quân", "Viện CNTT & KTS", "dangminhquan", 50000, False),
    ("GV004", "Nguyễn Văn Minh", "Viện Kế toán - Kiểm toán", "nguyenvanminh", 50000, True),
    ("GV005", "Trần Thị Mai", "Khoa Tài chính - Ngân hàng", "tranthimai", 50000, False),
    ("GV006", "Lê Hoàng Nam", "Phòng Quản trị - Thiết bị", "lehoangnam", 50000, False),
]
