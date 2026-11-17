# Thuật toán hệ thống nhận diện phương tiện đi sai làn

Tài liệu mô tả luồng xử lý và thuật toán xác định phương tiện đi sai làn đường
trong dự án ITS-WrongLaneDetection.

## 1. Tổng quan luồng xử lý

```
Video → Tách khung hình → Phát hiện xe (YOLO) + Gán ID (ByteTrack)
      → Xác định làn của từng xe → Xác nhận vi phạm theo quy tắc → Lưu bằng chứng và cảnh báo
```

| Bước | Thành phần | Vai trò |
|------|-----------|---------|
| 1 | `core/video_processor.py` (`VideoProcessor`) | Đọc video, xử lý từng khung hình, vẽ kết quả, xuất video và tổng hợp kết quả |
| 2 | `core/tracker.py` (`VehicleTracker`, bọc `core/detector.py`) | YOLO phát hiện xe; ByteTrack gán và duy trì `track_id` |
| 3 | `core/lane_detector.py` (`LaneDetector`) | Xác định làn của xe từ polygon làn cấu hình thủ công |
| 4 | `core/wrong_lane_detector.py` (`WrongLaneDetector`) | Xác nhận chuyển làn bị cấm qua nhiều khung hình |
| 5 | `core/alert_manager.py` (`AlertManager`) | Lưu ảnh bằng chứng cho mỗi vi phạm |

Hệ thống sử dụng YOLO, ByteTrack và OpenCV; làn đường được cấu hình thủ công theo polygon
(`configs/lanes_selected.json`), không tự động nhận dạng vạch kẻ đường.

## 2. Xử lý trong từng khung hình

Với mỗi khung hình đọc được từ video, `VideoProcessor.process()` thực hiện:

1. Tính `frame_index` (bắt đầu từ 1) và `timestamp = (frame_index - 1) / fps`.
2. Gọi `VehicleTracker.update(frame)` để nhận danh sách xe. Mỗi xe có bounding box,
   loại xe, confidence và `track_id`.
3. Vẽ các polygon làn lên khung hình.
4. Với mỗi xe có `track_id`:
   1. Lấy **điểm chân** của xe từ bounding box bằng `vehicle_foot_point()`
      (điểm tiếp xúc với mặt đường).
   2. Gọi `LaneDetector.lane_at(điểm_chân)` để tìm làn chứa điểm này. Kết quả là
      `lane_id`, hoặc `None` nếu điểm nằm ngoài mọi làn.
   3. Gọi `WrongLaneDetector.update(track_id, lane_id, frame_index, timestamp)`.
   4. Cập nhật dữ liệu nhận diện của xe (loại xe, làn gần nhất, trạng thái vi phạm).
   5. Nếu có vi phạm: đổi màu khung xe sang đỏ với nhãn `WRONG LANE`, lưu ảnh bằng chứng
      qua `AlertManager.save_evidence()`, ghi nhận vào danh sách vi phạm.
5. Ghi khung hình đã vẽ vào video đầu ra và cập nhật tiến độ (tối đa 99% cho đến khi xử lý xong).

Dùng điểm chân thay vì tâm bounding box giúp vị trí xe trên mặt đường ổn định hơn,
nhất là với camera đặt trên cao.

## 3. Dữ liệu đầu vào của bộ nhận diện

`WrongLaneDetector.update()` nhận, cho mỗi xe trong mỗi khung hình:

- `track_id`: ID của xe do bộ theo dõi gán.
- `lane_id`: làn xe đang đứng (chuỗi), hoặc `None` nếu xe ngoài mọi làn.
- `frame_index`: số thứ tự khung hình.
- `timestamp_seconds`: thời điểm của khung hình trong video (giây).

Cấu hình khi khởi tạo:

- `forbidden_transitions`: tập các cặp `(làn_nguồn, làn_đích)` bị cấm.
  Ví dụ `{("lane_2", "lane_3")}` nghĩa là chuyển từ `lane_2` sang `lane_3` là vi phạm.
- `confirm_frames` (mặc định 8, tối thiểu 1): số khung hình liên tiếp xe phải ở làn đích để xác nhận.
  Giá trị nhỏ hơn 1 sẽ gây `ValueError`.

Nếu chưa có làn hoặc `forbidden_transitions` rỗng, hệ thống không đánh giá sai làn:
kết quả có `analysis_scope = "detection_only"` kèm cảnh báo tương ứng.

## 4. Quy tắc nhận diện

Xe bị coi là đi sai làn khi **chuyển từ làn A sang làn B thuộc `forbidden_transitions`
và ở lại làn B đủ `confirm_frames` khung hình**. Việc xác nhận nhiều khung hình giúp loại
bỏ nhiễu do bounding box chạm mép làn hoặc xe chỉ lấn làn thoáng qua.

### 4.1 Trạng thái lưu cho mỗi xe

Với mỗi `track_id`, bộ nhận diện lưu một bộ ba:

```
(làn hiện tại, làn xuất phát của lần chuyển cấm, số khung đã xác nhận)
```

- `làn xuất phát = None` và đếm = 0: xe đang đi bình thường.
- `làn xuất phát ≠ None`: xe vừa thực hiện chuyển làn cấm và đang được xác nhận.

### 4.2 Các trường hợp xử lý trong mỗi lần `update()`

1. **`lane_id` là `None`** (xe ngoài mọi làn): giữ làn hiện tại cũ, đặt bộ đếm về 0,
   không báo vi phạm.
2. **Xe xuất hiện lần đầu**: ghi nhận làn hiện tại, chưa có chuyển làn, không báo.
3. **Xe vẫn ở cùng làn**:
   - Nếu đang xác nhận một lần chuyển cấm: tăng bộ đếm. Khi bộ đếm đạt `confirm_frames`
     và cặp `(track_id, làn_nguồn, làn_đích)` chưa từng báo, trả về một `Violation`.
   - Nếu không: không làm gì.
4. **Xe đổi làn**:
   - Cặp `(làn cũ, làn mới)` thuộc `forbidden_transitions`: ghi nhận làn mới, lưu làn
     xuất phát, đặt bộ đếm = 1. Nếu `confirm_frames == 1` thì báo ngay.
   - Ngược lại (chuyển làn hợp lệ): đặt trạng thái bình thường, xóa quá trình xác nhận.

### 4.3 Chống báo trùng

Tập `_reported` lưu các khóa `(track_id, làn_nguồn, làn_đích)` đã báo. Mỗi xe với mỗi cặp
làn chỉ bị báo **một lần**, kể cả khi xe tiếp tục ở làn đó nhiều khung hình sau.

## 5. Mã giả

```
update(track_id, lane_id, frame, time):
    nếu lane_id là None:
        nếu xe đã có trạng thái: đặt đếm = 0 và xóa làn xuất phát
        trả về None
    nếu xe chưa có trạng thái:
        lưu (lane_id, None, 0); trả về None
    (làn_cũ, xuất_phát, đếm) = trạng thái
    nếu lane_id == làn_cũ:
        nếu xuất_phát khác None:
            đếm += 1
            nếu đếm >= confirm_frames và chưa báo (track_id, xuất_phát, làn_cũ):
                đánh dấu đã báo; trả về Violation
        trả về None
    nếu (làn_cũ, lane_id) thuộc forbidden_transitions:
        lưu (lane_id, làn_cũ, 1)
        nếu confirm_frames == 1 và chưa báo: đánh dấu đã báo; trả về Violation
        trả về None
    lưu (lane_id, None, 0); trả về None
```

## 6. Đầu ra

### 6.1 Đối tượng vi phạm

Khi xác nhận vi phạm, `update()` trả về một `Violation` (`backend/models/violation.py`) gồm:
`track_id`, `source_lane`, `destination_lane`, `frame_index`, `timestamp_seconds`.
`frame_index` và `timestamp_seconds` là của **khung hình xác nhận** (khung thứ `confirm_frames`
kể từ khi chuyển làn), không phải khung hình bắt đầu chuyển làn.
Sau đó `VideoProcessor` bổ sung `evidence_path` (đường dẫn ảnh bằng chứng) nếu lưu được.

### 6.2 Kết quả tổng hợp sau khi xử lý video

`VideoProcessor.process()` trả về một từ điển (schema `DetectionResultSummary`):

| Trường | Ý nghĩa |
|--------|---------|
| `processed_frames` | Số khung hình đã xử lý |
| `unique_tracked_vehicles` | Số xe khác nhau (theo `track_id`) |
| `vehicle_type_counts` | Số xe theo loại (`car`, `truck`, `bus`, ...) |
| `vehicles` | Danh sách dữ liệu nhận diện từng xe (xem 6.3) |
| `violation_count` | Số vi phạm phát hiện được |
| `violations` | Chi tiết từng vi phạm |
| `processing_seconds` | Thời gian xử lý (giây) |
| `analysis_scope` | `configured_lane_rules` hoặc `detection_only` |
| `warnings` | Cảnh báo cấu hình (thiếu làn, thiếu quy tắc chuyển làn cấm) |

### 6.3 Dữ liệu nhận diện của từng xe

Mỗi phần tử trong `vehicles` (schema `VehicleDetectionRead`) gồm:

| Trường | Ý nghĩa |
|--------|---------|
| `track_id` | ID theo dõi của xe |
| `vehicle_type` | Loại xe |
| `lane_id` | Làn hợp lệ gần nhất mà xe được quan sát (không bị ghi đè bởi `None`) |
| `violation_status` | `detected` hoặc `not_detected` |
| `source_lane`, `destination_lane` | Làn trước và sau khi chuyển làn vi phạm (nếu có) |
| `frame_index`, `timestamp_seconds` | Khung hình và thời điểm xe được thấy gần nhất |

Nếu một xe vi phạm nhiều cặp làn khác nhau, `source_lane` và `destination_lane` trong
`vehicles` chỉ giữ vi phạm gần nhất; danh sách `violations` vẫn ghi đầy đủ từng vi phạm.

## 7. Tham số và độ nhạy

| Tham số | Mặc định | Ảnh hưởng |
|---------|----------|-----------|
| `confirm_frames` | 8 | Tăng: ít báo nhầm nhưng báo trễ hơn. Giảm: nhạy hơn nhưng dễ nhiễu |
| `forbidden_transitions` | cấu hình | Xác định chuyển làn nào bị coi là vi phạm |

`confirm_frames` tính theo khung hình. Thời gian xác nhận tương ứng là `confirm_frames / fps`
giây (ví dụ 8 khung ở 30 fps ≈ 0,27 giây).

## 8. Hạn chế đã biết

- Xe mất làn (`lane_id = None`) dù chỉ một khung sẽ làm bộ đếm xác nhận về 0.
- Trạng thái theo từng `track_id` chỉ tăng theo thời gian, chưa có cơ chế dọn các track đã biến mất.
- Phụ thuộc vào độ ổn định của ID: nếu bộ theo dõi đổi ID giữa chừng, quá trình xác nhận bắt đầu lại.
- Làn đường cấu hình thủ công theo polygon, nên mỗi góc camera cần cấu hình riêng.
- Vi phạm được xác nhận ở khung thứ `confirm_frames`, nên thời điểm báo trễ hơn thời điểm chuyển làn thực tế.
