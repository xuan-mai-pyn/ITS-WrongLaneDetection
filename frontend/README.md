# Frontend - ITS Wrong-Lane Detection

Giao diện người dùng (Web UI) cho hệ thống giám sát và phát hiện phương tiện đi sai làn đường (**ITS-WrongLaneDetection**), xây dựng bằng HTML5, CSS3 thuần và Vanilla JavaScript kết nối với Backend FastAPI.

## Cấu trúc thư mục

```text
frontend/
├── index.html                  # Trang gốc điều hướng nhanh sang Dashboard
├── README.md                   # Tài liệu mô tả cấu trúc và cách chạy Frontend
├── pages/
│   ├── dashboard.html          # Tổng quan hệ thống, thẻ chỉ số & biểu đồ thống kê
│   ├── detection.html          # Tải video lên, theo dõi tiến trình & xem kết quả nhận diện
│   ├── history.html            # Tra cứu lịch sử video đã xử lý & bộ lọc vi phạm
│   └── statistics.html         # Phân tích chi tiết tỷ lệ vi phạm & tổng hợp số liệu
└── assets/
    ├── css/
    │   ├── style.css           # Giao diện dùng chung (Sidebar, Layout, Bảng, Tag trạng thái)
    │   ├── dashboard.css       # Kiểu dáng biểu đồ thanh ngang cho Dashboard & Statistics
    │   └── detection.css       # Kiểu dáng khu vực tải video, khung xem trước & thanh tiến trình
    └── js/
        ├── api.js              # Lớp giao tiếp chuẩn hóa với các endpoint /api/* của FastAPI
        ├── main.js             # Tiện ích dùng chung (định dạng ngày, tag trạng thái, toast, kiểm tra API)
        ├── dashboard.js        # Nạp số liệu tổng quan, biểu đồ & danh sách video gần đây
        ├── detection.js        # Xử lý upload video, kích hoạt nhận diện & polling trạng thái tác vụ
        ├── history.js          # Hiển thị lịch sử video & lọc danh sách vi phạm theo làn/loại xe
        └── statistics.js       # Tổng hợp và trực quan hóa dữ liệu thống kê chi tiết
