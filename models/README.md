# Mô hình sử dụng trong hệ thống

Thư mục này mô tả các mô hình dùng để nhận diện phương tiện đi sai làn đường.
Các mục có dấu **[CẦN ĐIỀN]** cần thay bằng thông tin thực tế của dự án.

## 1. Mô hình phát hiện phương tiện (YOLO)

| Thông tin | Giá trị |
|-----------|---------|
| Họ mô hình | YOLO (Ultralytics) |
| Phiên bản | **[CẦN ĐIỀN]** (ví dụ YOLOv8n) |
| File trọng số | **[CẦN ĐIỀN]** (ví dụ `yolov8n.pt`) |
| Vị trí file | `models/weights/` (thư mục gốc dự án) |
| Thiết bị chạy | CPU (không bắt buộc GPU) |
| Mã nguồn sử dụng | `backend/core/detector.py` (lớp `YOLODetector`) |

Các loại phương tiện được giữ lại: ô tô (`car`), xe máy (`motorcycle`), xe buýt (`bus`), xe tải (`truck`).
Các lớp khác bị bỏ qua. Mỗi phát hiện gồm bounding box, loại xe và confidence score.

## 2. Theo dõi phương tiện (ByteTrack)

| Thông tin | Giá trị |
|-----------|---------|
| Thuật toán | ByteTrack |
| Mã nguồn | `backend/core/tracker.py` |
| Vai trò | Gán và duy trì `track_id` cho mỗi xe qua các khung hình |

ByteTrack nhận kết quả phát hiện của YOLO ở từng khung hình và trả về cùng bounding box
kèm `track_id`. ID này là khóa để `WrongLaneDetector` theo dõi lịch sử làn của từng xe.

## 3. Cách chuẩn bị trọng số

1. Tải file trọng số YOLO và đặt vào `models/weights/`.
2. Kiểm tra đường dẫn trọng số trong cấu hình/khởi tạo của `YOLODetector`.
3. Chạy backend (`scripts/run_backend.py`) và gọi thử `GET /api/videos` để kiểm tra.

File trọng số có dung lượng lớn nên **không nên commit lên Git**; thêm `models/weights/` vào `.gitignore`
nếu chưa có và chia sẻ file qua kênh chung của nhóm.

## 4. Lưu ý

- Chạy trên CPU nên tốc độ xử lý phụ thuộc cấu hình máy và độ phân giải video.
- Mô hình chỉ phát hiện và theo dõi xe. Việc xác định sai làn do `core/wrong_lane_detector.py`
  xử lý bằng quy tắc, không dùng mô hình học máy riêng (xem `docs/algorithms.md`).
