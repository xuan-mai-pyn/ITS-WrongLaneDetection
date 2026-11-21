"""
Quản lý cấu hình tập trung cho toàn bộ Backend.

Cách sử dụng:
    from backend.config import Settings
    settings = Settings()
    print(settings.model_path)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

# ── Xác định thư mục gốc của dự án (thư mục cha của backend/) ──
PROJECT_ROOT = Path(__file__).resolve().parents[1]

try:
    from dotenv import load_dotenv
    # ── Đọc file .env nếu tồn tại ──
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

# ── Các định dạng video được phép upload ──
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}

# ── Cấu hình logging mặc định ──
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_LEVEL = os.getenv("ITS_LOG_LEVEL", "INFO").upper()


def _project_path(value: str) -> Path:
    """
    Chuyển chuỗi đường dẫn thành Path tuyệt đối.

    - Nếu đường dẫn đã là tuyệt đối → giữ nguyên.
    - Nếu đường dẫn tương đối → ghép với PROJECT_ROOT.

    Ví dụ:
        _project_path("storage/uploads")
        → D:/ITSTL/storage/uploads
    """
    path = Path(value).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


def setup_logging() -> None:
    """
    Thiết lập logging cho toàn bộ ứng dụng.

    Gọi hàm này một lần khi khởi động Backend để các module
    có thể dùng logging.getLogger(__name__) ghi log thống nhất.
    """
    logging.basicConfig(format=LOG_FORMAT, level=LOG_LEVEL)


@dataclass(frozen=True)
class Settings:
    """
    Lưu trữ toàn bộ cấu hình của ứng dụng.

    Các giá trị được đọc từ biến môi trường (file .env).
    Nếu biến không tồn tại, sử dụng giá trị mặc định.

    Thuộc tính:
        project_root            : Đường dẫn thư mục gốc dự án.
        database_path           : Đường dẫn file SQLite database.
        upload_dir              : Thư mục lưu video người dùng tải lên.
        processed_dir           : Thư mục lưu video đã xử lý (có bounding box).
        evidence_dir            : Thư mục lưu ảnh minh chứng vi phạm.
        model_path              : Đường dẫn file trọng số YOLO (.pt).
        lane_config_path        : Đường dẫn file JSON cấu hình làn đường (tùy chọn).
        max_upload_bytes        : Giới hạn dung lượng upload (mặc định 500MB).
        violation_confirm_frames: Số frame liên tiếp để xác nhận vi phạm (mặc định 8).
        host                    : Địa chỉ IP chạy server (mặc định 127.0.0.1).
        port                    : Cổng chạy server (mặc định 8000).
        allowed_extensions      : Các định dạng video được phép upload.
    """

    # ── Đường dẫn thư mục gốc ──
    project_root: Path = PROJECT_ROOT

    # ── Đường dẫn database SQLite ──
    database_path: Path = _project_path(
        os.getenv("ITS_DATABASE_PATH", "storage/its_wrong_lane.db")
    )

    # ── Các thư mục lưu trữ ──
    upload_dir: Path = _project_path(
        os.getenv("ITS_UPLOAD_DIR", "storage/uploads")
    )
    processed_dir: Path = _project_path(
        os.getenv("ITS_PROCESSED_DIR", "storage/processed")
    )
    evidence_dir: Path = _project_path(
        os.getenv("ITS_EVIDENCE_DIR", "storage/evidence")
    )

    # ── Đường dẫn trọng số mô hình YOLO ──
    model_path: Path = _project_path(
        os.getenv("ITS_MODEL_PATH", "models/weights/yolov8n.pt")
    )

    # ── Đường dẫn file cấu hình làn đường (None nếu chưa cấu hình) ──
    lane_config_path: Path | None = (
        _project_path(
            os.getenv(
                "ITS_LANE_CONFIG",
                "configs/lanes_selected.json",
            )
        )
    )

    # ── Giới hạn dung lượng file upload (byte) ── mặc định 500MB ──
    max_upload_bytes: int = int(
        os.getenv("ITS_MAX_UPLOAD_BYTES", "524288000")
    )

    # ── Số frame liên tiếp cần quan sát để xác nhận vi phạm sai làn ──
    violation_confirm_frames: int = int(
        os.getenv("ITS_VIOLATION_CONFIRM_FRAMES", "8")
    )

    # ── Cấu hình máy chủ ──
    host: str = os.getenv("ITS_HOST", "127.0.0.1")
    port: int = int(os.getenv("ITS_PORT", "8000"))

    # ── Định dạng video được phép ──
    allowed_extensions: frozenset = field(
        default_factory=lambda: frozenset(ALLOWED_VIDEO_EXTENSIONS)
    )

    def prepare_directories(self) -> None:
        """
        Tạo các thư mục cần thiết nếu chưa tồn tại.

        Được gọi một lần khi khởi động ứng dụng trong main.py
        để đảm bảo các thư mục lưu trữ sẵn sàng trước khi
        nhận video upload hoặc xử lý.
        """
        for directory in (
            self.database_path.parent,
            self.upload_dir,
            self.processed_dir,
            self.evidence_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    def validate(self) -> list[str]:
        """
        Kiểm tra cấu hình và trả về danh sách cảnh báo.

        Không raise exception mà trả về list các vấn đề
        để Backend vẫn khởi động được (ở chế độ hạn chế)
        và hiển thị lỗi rõ ràng khi người dùng thực hiện
        thao tác cần thành phần chưa sẵn sàng.

        Returns:
            Danh sách chuỗi mô tả các vấn đề cấu hình (rỗng nếu OK).
        """
        warnings: list[str] = []

        # Kiểm tra file trọng số YOLO
        if not self.model_path.is_file():
            warnings.append(
                f"File trọng số YOLO không tồn tại: {self.model_path}. "
                "Chức năng phát hiện phương tiện sẽ không hoạt động."
            )

        # Kiểm tra cấu hình làn đường
        if self.lane_config_path is None:
            warnings.append(
                "Chưa cấu hình ITS_LANE_CONFIG. "
                "Hệ thống chỉ phát hiện phương tiện, không đánh giá sai làn."
            )
        elif not self.lane_config_path.is_file():
            warnings.append(
                f"File cấu hình làn đường không tồn tại: {self.lane_config_path}."
            )

        # Kiểm tra giá trị hợp lệ
        if self.max_upload_bytes <= 0:
            warnings.append("max_upload_bytes phải lớn hơn 0.")

        if self.violation_confirm_frames < 1:
            warnings.append("violation_confirm_frames phải từ 1 trở lên.")

        if not (1 <= self.port <= 65535):
            warnings.append(f"Port {self.port} nằm ngoài phạm vi hợp lệ (1-65535).")

        return warnings
