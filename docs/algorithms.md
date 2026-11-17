# Thuật toán hệ thống nhận diện phương tiện đi sai làn

Tài liệu mô tả luồng xử lý và thuật toán xác định phương tiện đi sai làn.
Các mục có dấu **[CẦN XÁC NHẬN]** là chỗ cần đối chiếu lại với mã nguồn thực tế trước khi nộp.

## 1. Tổng quan luồng xử lý

```
Video → Tách khung hình → YOLO (phát hiện xe) → ByteTrack (gán ID)
      → Xác định làn của từng xe → WrongLaneDetector → Violation → Lưu/Cảnh báo
```

| Bước | Thành phần | Vai trò |
|------|-----------|---------|
| 1 | `core/video_processor.py` | Đọc video, đưa từng khung hình qua các bước sau |
| 2 | `core/detector.py` | YOLO phát hiện xe: bounding box, loại xe, confidence |
| 3 | `core/tracker.py` | Gán và duy trì ID (`track_id`) cho từng xe qua các khung hình |
| 4 | Xác định làn | Đối chiếu vị trí xe với polygon làn đường cấu hình thủ công |
| 5 | `core/wrong_lane_detector.py` | Xác nhận vi phạm theo quy tắc, nhiều khung hình liên tiếp |

## 2. Dữ liệu đầu vào của bộ nhận diện

Với mỗi xe trong mỗi khung hình, `WrongLaneDetector.update()` nhận:

- `track_id`: ID của xe do bộ theo dõi gán.
- `lane_id`: làn xe đang đứng (chuỗi), hoặc `None` nếu xe không nằm trong làn nào.
- `frame_index`: số thứ tự khung hình.
- `timestamp_seconds`: thời điểm của khung hình trong video.

Cấu hình:

- `forbidden_transitions`: tập các cặp `(làn_nguồn, làn_đích)` bị cấm.
  Ví dụ `{("lane_2", "lane_3")}` nghĩa là chuyển từ `lane_2` sang `lane_3` là vi phạm.
- `confirm_frames` (mặc định 8, tối thiểu 1): số khung hình liên tiếp xe phải ở làn đích để xác nhận.

Nếu `forbidden_transitions` rỗng, bộ nhận diện không báo vi phạm nào.

## 3. Quy tắc nhận diện

Xe bị coi là đi sai làn khi **chuyển từ làn A sang làn B thuộc `forbidden_transitions`
và ở lại làn B đủ `confirm_frames` khung hình**. Việc xác nhận nhiều khung hình giúp loại
bỏ nhiễu do bounding box chạm mép làn hoặc xe chỉ lấn làn thoáng qua.

### 3.1 Trạng thái lưu cho mỗi xe

Với mỗi `track_id`, bộ nhận diện lưu một bộ ba:

```
(làn hiện tại, làn xuất phát của lần chuyển cấm, số khung đã xác nhận)
```

- `làn xuất phát = None` và đếm = 0: xe đang đi bình thường.
- `làn xuất phát ≠ None`: xe vừa thực hiện chuyển làn cấm và đang được xác nhận.

### 3.2 Các trường hợp xử lý trong mỗi lần `update()`

1. **`lane_id` là `None`** (xe ngoài mọi làn): giữ làn hiện tại cũ, đặt lại bộ đếm về 0,
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

### 3.3 Chống báo trùng

Tập `_reported` lưu các khóa `(track_id, làn_nguồn, làn_đích)` đã báo. Mỗi xe với mỗi cặp
làn chỉ bị báo **một lần**, kể cả khi xe tiếp tục ở làn đó nhiều khung hình sau.

## 4. Đầu ra

Khi xác nhận vi phạm, `update()` trả về một đối tượng `Violation` (`backend/models/violation.py`)
gồm: `track_id`, `source_lane`, `destination_lane`, `frame_index`, `timestamp_seconds`.
`frame_index` và `timestamp_seconds` là của **khung hình xác nhận** (khung thứ `confirm_frames`
kể từ khi chuyển làn), không phải khung hình bắt đầu chuyển làn.

## 5. Mã giả

```
update(track_id, lane_id, frame, time):
    nếu lane_id là None:
        đặt đếm = 0 và xóa làn xuất phát (nếu xe đã có trạng thái); trả về None
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

## 6. Tham số và độ nhạy

| Tham số | Mặc định | Ảnh hưởng |
|---------|----------|-----------|
| `confirm_frames` | 8 | Tăng: ít báo nhầm nhưng báo trễ hơn. Giảm: nhạy hơn nhưng dễ nhiễu |
| `forbidden_transitions` | (cấu hình) | Xác định chuyển làn nào bị coi là vi phạm |

`confirm_frames` tính theo khung hình. Thời gian xác nhận tương ứng là `confirm_frames / fps`
giây (ví dụ 8 khung ở 30 fps ≈ 0,27 giây).

## 7. Hạn chế đã biết

- Xe mất làn (`lane_id = None`) dù chỉ một khung sẽ làm bộ đếm xác nhận về 0.
- Trạng thái theo từng `track_id` chỉ tăng theo thời gian, chưa có cơ chế dọn các track đã biến mất.
- Phụ thuộc vào độ ổn định của ID: nếu bộ theo dõi đổi ID giữa chừng, quá trình xác nhận bắt đầu lại.
- Làn đường được cấu hình thủ công theo polygon (`configs/lanes_selected.json`), nên mỗi camera cần cấu hình riêng.

## 8. Cách xác định làn từ vị trí xe

**[CẦN XÁC NHẬN]** Điền theo mã thực tế: điểm đại diện của xe (ví dụ trung điểm cạnh dưới của
bounding box) được kiểm tra nằm trong polygon của làn nào (ví dụ `cv2.pointPolygonTest`).
