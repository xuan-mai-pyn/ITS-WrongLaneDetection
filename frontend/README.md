# Frontend - ITS Wrong-Lane Detection

Giao diện người dùng Web cho hệ thống nhận diện phương tiện đi sai làn đường. Frontend được xây dựng bằng HTML5, CSS3 và JavaScript thuần, sau đó giao tiếp với Backend qua REST API để tải video, theo dõi tác vụ phân tích và hiển thị kết quả.

Frontend không thực hiện phát hiện phương tiện, nhận diện YOLO, theo dõi ByteTrack, xử lý OpenCV hoặc xác định vi phạm. Các thuật toán này thuộc về Backend.

## 1. Mục tiêu và phạm vi

Mục tiêu của Frontend là:

- Cung cấp giao diện cho người dùng tải video giao thông.
- Gửi yêu cầu tải video và chạy phân tích đến Backend.
- Theo dõi trạng thái và tiến độ xử lý của tác vụ.
- Hiển thị video kết quả, số liệu tổng hợp và danh sách vi phạm.
- Cung cấp công cụ tìm kiếm, lọc và thống kê trên dữ liệu do Backend trả về.
- Hiển thị trạng thái kết nối API, cơ sở dữ liệu, mô hình nhận diện và cấu hình làn đường.

Frontend chỉ đảm nhiệm giao diện, tương tác người dùng và giao tiếp API. Việc xác định phương tiện nằm trong Polygon không đồng nghĩa phương tiện đã vi phạm; hành vi sai làn được Backend xác nhận dựa trên quy tắc chuyển làn và nhiều khung hình.

## 2. Công nghệ sử dụng

- HTML5 để xây dựng cấu trúc trang.
- CSS3 để bố trí, thiết kế responsive và tạo trạng thái giao diện.
- JavaScript thuần để xử lý tương tác, trạng thái và gọi API.
- REST API để liên lạc với Backend FastAPI.
- Fetch API của trình duyệt để gửi yêu cầu HTTP và xử lý JSON.

Mã nguồn Frontend không sử dụng React, Vue, Angular, Bootstrap hoặc framework JavaScript/CSS khác.

## 3. Cấu trúc thư mục thực tế

```text
frontend/
├── index.html
├── README.md
├── pages/
│   ├── dashboard.html
│   ├── detection.html
│   ├── history.html
│   └── statistics.html
└── assets/
    ├── css/
    │   ├── style.css
    │   ├── dashboard.css
    │   ├── detection.css
    │   ├── history.css
    │   └── statistics.css
    ├── js/
    │   ├── api.js
    │   ├── main.js
    │   ├── dashboard.js
    │   ├── detection.js
    │   ├── history.js
    │   └── statistics.js
    └── images/
        └── .gitkeep
```

Các trang chính sử dụng đường dẫn tuyệt đối `/dashboard`, `/detection`, `/history` và `/statistics`, do đó Frontend được phục vụ thông qua Backend thay vì mở trực tiếp các file HTML như trang web độc lập.

## 4. Trang điều hướng

### 4.1. Trang khởi động

Tệp `frontend/index.html` hiển thị trạng thái chuyển hướng ngắn và tự chuyển tới `/dashboard`. Trang còn có liên kết thủ công nếu trình duyệt không thực hiện chuyển hướng tự động.

## 5. Mô tả các trang chức năng

### 5.1. Dashboard

Các file liên quan:

- `frontend/pages/dashboard.html`
- `frontend/assets/css/dashboard.css`
- `frontend/assets/js/dashboard.js`

Trang Dashboard hiển thị:

- Số video đã xử lý.
- Tổng số phương tiện theo dõi.
- Tổng lượt vi phạm.
- Tỷ lệ phát hiện do Backend cung cấp.
- Biểu đồ tổng hợp các chỉ số.
- Danh sách tối đa sáu video xử lý gần đây.
- Trạng thái kết nối API, cơ sở dữ liệu, mô hình YOLO và cấu hình làn đường.
- Cảnh báo của Backend nếu có.

Dashboard gọi độc lập API thống kê, danh sách video và trạng thái hệ thống bằng `Promise.allSettled`. Cách xử lý này giúp một yêu cầu lỗi không làm hỏng toàn bộ nội dung của trang. Nút làm mới dữ liệu cho phép tải lại dữ liệu khi cần.

### 5.2. Detection

Các file liên quan:

- `frontend/pages/detection.html`
- `frontend/assets/css/detection.css`
- `frontend/assets/js/detection.js`

Trang nhận diện cho phép người dùng:

- Chọn video bằng hộp thoại file hoặc kéo thả.
- Xem tên, dung lượng và bản xem trước video.
- Xóa hoặc chọn lại video trước khi xử lý.
- Tải video lên Backend.
- Khởi động tác vụ nhận diện.
- Theo dõi trạng thái, phần trăm tiến độ và số khung hình đã xử lý.
- Xem tóm tắt kết quả và video kết quả nếu đường dẫn đầu ra hiện có.

Luồng tương tác được quản lý bằng một số trạng thái:

- Khóa input, nút xóa, nút bắt đầu và khu vực kéo thả khi tác vụ đang chạy.
- Ngăn khởi tạo nhiều tác vụ trùng lặp.
- Khôi phục tương tác khi upload hoặc khởi chạy tác vụ thất bại.
- Dừng theo dõi khi tác vụ thất bại, mất kết nối API liên tục hoặc hết thời gian chờ.
- Thu hồi URL xem trước bằng `URL.revokeObjectURL` khi chọn file khác hoặc thoát trang.

Kết quả được xử lý bởi hàm `renderResult(task)` và được chờ hoàn tất bằng `await renderResult(task)` sau khi tác vụ chuyển sang trạng thái hoàn thành.

### 5.3. History

Các file liên quan:

- `frontend/pages/history.html`
- `frontend/assets/css/history.css`
- `frontend/assets/js/history.js`

Trang lịch sử hiển thị:

- Danh sách video đã tải lên, thời gian tải, trạng thái và số liệu xử lý.
- Nhật ký các bản ghi vi phạm do Backend lưu trữ.
- Mã xe, mã video, loại phương tiện, làn nguồn, làn đích và thời điểm ghi nhận.
- Chế độ loại phương tiện `unknown` khi dữ liệu không xác định được loại xe.

Người dùng có thể tìm theo mã xe, mã video hoặc tên làn, đồng thời lọc theo loại phương tiện. Dữ liệu hiển thị trong HTML được xử lý bằng hàm escape để hạn chế nội dung không an toàn được chèn trực tiếp vào giao diện.

### 5.4. Statistics

Các file liên quan:

- `frontend/pages/statistics.html`
- `frontend/assets/css/statistics.css`
- `frontend/assets/js/statistics.js`

Trang thống kê lấy số liệu tổng hợp và danh sách vi phạm từ Backend, sau đó trình bày:

- Số video đã xử lý.
- Tổng phương tiện theo dõi.
- Tổng lượt vi phạm.
- Tỷ lệ phát hiện do Backend cung cấp.
- Phân bổ số lượt vi phạm theo loại phương tiện.

Biểu đồ phân loại phương tiện phản ánh các bản ghi vi phạm được lưu trữ, không phải tổng số phương tiện xuất hiện trong toàn bộ video.

## 6. Giao tiếp với Backend

Tệp `frontend/assets/js/api.js` tập trung các hàm gọi REST API:

| Chức năng                    | Phương thức | Endpoint                         |
| ---------------------------- | ----------- | -------------------------------- |
| Kiểm tra tình trạng hệ thống | `GET`       | `/api/health`                    |
| Lấy thống kê                 | `GET`       | `/api/statistics`                |
| Lấy danh sách video          | `GET`       | `/api/videos`                    |
| Lấy danh sách vi phạm        | `GET`       | `/api/violations`                |
| Tải video                    | `POST`      | `/api/videos/upload`             |
| Khởi chạy phát hiện          | `POST`      | `/api/detection/start`           |
| Lấy trạng thái tác vụ        | `GET`       | `/api/detection/{taskId}/status` |
| Lấy video kết quả            | `GET`       | `/api/detection/{taskId}/video`  |

Các hàm trong `api.js` gửi request bằng `fetch`, phân tích phản hồi JSON và ném lỗi có thông điệp từ `detail` hoặc `message` của Backend khi HTTP response không thành công. Trong trang nhận diện, trạng thái tác vụ được truy vấn định kỳ bằng polling khoảng 1,2 giây.

Tệp `frontend/assets/js/main.js` cung cấp các tiện ích dùng chung:

- `formatBytes` để định dạng dung lượng file.
- `formatDate` để định dạng thời gian.
- `statusTag` để hiển thị trạng thái video.
- `escapeHtml` để mã hóa nội dung trước khi hiển thị.
- `vehicleTypeName` để ánh xạ loại phương tiện.
- `showToast` để hiển thị thông báo.
- Kiểm tra trạng thái Backend trên thanh điều hướng.

## 7. Giao diện và trải nghiệm người dùng

- Giao diện dùng chung được tập trung trong `style.css`.
- CSS riêng cho từng trang được đặt trong các file tương ứng.
- Thanh điều hướng được đánh dấu trang đang hoạt động.
- Đồng hồ trên đầu trang được cập nhật theo định kỳ.
- Các thành phần tương tác hỗ trợ trạng thái `:focus-visible`.
- Khu vực tải video hỗ trợ điều hướng bàn phím thông qua `label` và input file.
- Các bảng dữ liệu được bao bởi vùng cuộn ngang để hạn chế tràn nội dung.
- Giao diện có bố cục responsive ở kích thước điện thoại, máy tính bảng và máy tính.

Các breakpoint đã có trong CSS bao gồm bố cục ở 1080px, 768px, 600px và 360px. Việc kiểm tra trên trình duyệt đã được rà soát ở các nhóm kích thước 320px, 390px, 768px, 1366px và 1920px theo phạm vi Frontend được cung cấp.

## 8. Xử lý lỗi và trạng thái

Frontend xử lý các tình huống:

- Backend không phản hồi hoặc API ngoại tuyến.
- API trả về HTTP lỗi.
- Tải video thất bại.
- Khởi chạy tác vụ thất bại.
- Mất kết nối trong khi polling.
- Tác vụ chuyển sang trạng thái thất bại.
- Tác vụ không kết thúc trong thời gian theo dõi.
- Không có dữ liệu video hoặc vi phạm.
- Không có dữ liệu thống kê.
- Video kết quả chưa sẵn sàng hoặc không thể tải.
- Tác vụ chưa tạo được kết quả.

Khi tải dữ liệu thất bại, trang hiển thị trạng thái rỗng hoặc thông báo lỗi thay vì suy ra dữ liệu giả. Các số liệu trên Dashboard và Statistics chỉ được lấy từ API hoặc mặc định bằng `0` trong khi chờ dữ liệu.

## 9. Kết quả kiểm tra

Trong quá trình rà soát Frontend đã kiểm tra các luồng sau theo kết quả được cung cấp:

- Tải video thành công và thất bại.
- Khởi chạy phân tích thành công và thất bại.
- Mất kết nối khi theo dõi tiến độ.
- Khôi phục trạng thái tương tác sau lỗi.
- Khóa và mở khóa thành phần giao diện trong lúc xử lý.
- Ngăn gửi nhiều tác vụ trùng lặp.
- Kéo thả video.
- Điều hướng bằng bàn phím.
- Hiển thị tại các kích thước 320px, 390px, 768px, 1366px và 1920px.

Các kết quả trên là kết quả kiểm thử phía Frontend; chưa có cơ sở để coi toàn hệ thống đã nghiệm thu. Không có bằng chứng trong repository rằng môi trường thực hiện đã cài Node.js hoặc đã chạy `node --check`, do đó README không ghi nhận kiểm tra bằng Node.js.

## 10. Tiến độ thực hiện

| STT | Hạng mục                               | Tiến độ                                       |
| --- | -------------------------------------- | --------------------------------------------- |
| 1   | Cấu trúc Frontend                      | Hoàn thành                                    |
| 2   | Trang Dashboard                        | Hoàn thành                                    |
| 3   | Trang Detection                        | Hoàn thành                                    |
| 4   | Trang History                          | Hoàn thành                                    |
| 5   | Trang Statistics                       | Hoàn thành                                    |
| 6   | Giao tiếp REST API                     | Đã triển khai                                 |
| 7   | Quản lý upload và trạng thái phân tích | Hoàn thành                                    |
| 8   | Xử lý lỗi và dữ liệu rỗng              | Hoàn thành                                    |
| 9   | Hỗ trợ bàn phím                        | Đã triển khai                                 |
| 10  | Responsive                             | Đã kiểm tra trong phạm vi kích thước nêu trên |
| 11  | Kiểm tra tương tác giao diện           | Đã thực hiện                                  |
| 12  | Tích hợp và kiểm thử toàn hệ thống     | Cần tiếp tục rà soát                          |

Frontend đã hoàn thành các trang chức năng chính và các cải tiến tương tác được mô tả trong tài liệu này. Giao diện đang kết nối bằng API hiện tại với Backend.

## 11. Công việc còn lại

- Kiểm thử tích hợp Frontend và Backend trong môi trường chạy đầy đủ.
- Xác minh dữ liệu thực tế qua toàn bộ luồng xử lý video.
- Rà soát các trường hợp lỗi phát sinh trong môi trường sử dụng thực tế.
- Tiếp tục hoàn thiện giao diện trước đợt nghiệm thu.

Không ghi rằng dự án đã hoàn thành 100% hoặc đã nghiệm thu nếu chưa có bằng chứng tương ứng.

## 12. Thông tin Git

- Repository: `https://github.com/xuan-mai-pyn/ITS-WrongLaneDetection.git`
- Nhánh đang làm việc: `fix/vehicle-type-history`
- Commit Backend: `6c24cde2892d856b0036f7d7c4c422759759626a` - `Improve backend vehicle tracking and wrong-lane detection`
- Commit Frontend: `be65ac844a0a208c879733226cf9b396fe1493a8` - `Improve frontend dashboard and detection experience`

Hai commit trên đã được xác nhận nằm trong lịch sử nhánh `fix/vehicle-type-history`.
