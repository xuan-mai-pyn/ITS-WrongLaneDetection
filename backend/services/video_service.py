"""
Dịch vụ nghiệp vụ quản lý Video: tiếp nhận, kiểm tra và lưu trữ video upload.

Chức năng chính:
    - Kiểm tra định dạng file video hợp lệ (mp4, avi, mov, mkv).
    - Đọc dữ liệu video theo từng chunk 1MB để tiết kiệm bộ nhớ RAM.
    - Kiểm tra dung lượng không vượt quá giới hạn max_upload_bytes.
    - Lưu file với tên UUID duy nhất vào thư mục storage/uploads/.
    - Tạo bản ghi metadata video trong database SQLite.
    - Tự động dọn dẹp file tạm nếu quá trình upload gặp lỗi.
"""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from backend.config import Settings
from backend.database.repository import Repository
from backend.schemas.video import VideoRead
from backend.utils.file_handler import validate_video_extension

logger = logging.getLogger(__name__)

# ── Kích thước mỗi lần đọc dữ liệu từ upload stream: 1MB ──
CHUNK_SIZE = 1024 * 1024

# ── Các định dạng video cho phép ──
ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}


class VideoService:
    """
    Dịch vụ xử lý nghiệp vụ liên quan đến video.

    Attributes:
        settings: Cấu hình hệ thống (đường dẫn, giới hạn dung lượng).
        repository: Đối tượng thao tác cơ sở dữ liệu.
    """

    def __init__(self, settings: Settings, repository: Repository) -> None:
        self.settings = settings
        self.repository = repository

    async def save_upload(self, upload: UploadFile) -> VideoRead:
        """
        Tiếp nhận, kiểm tra và lưu trữ file video từ người dùng.

        Quy trình:
            1. Trích xuất tên file gốc và kiểm tra phần mở rộng hợp lệ.
            2. Sinh mã UUID làm tên file lưu trữ (tránh trùng lặp và ký tự lạ).
            3. Đọc dữ liệu theo từng chunk 1MB và ghi ra ổ đĩa.
            4. Kiểm tra dung lượng tích lũy không vượt giới hạn max_upload_bytes.
            5. Nếu thành công: tạo bản ghi video trong database và trả về metadata.
            6. Nếu thất bại: xóa file tạm đã ghi dở và ném lại ngoại lệ.

        Args:
            upload: Đối tượng UploadFile từ FastAPI chứa dữ liệu video.

        Returns:
            VideoRead: Thông tin metadata của video vừa lưu thành công.

        Raises:
            ValueError: File rỗng, sai định dạng hoặc vượt giới hạn dung lượng.
        """
        # ── 1. Kiểm tra định dạng file ──
        original_name = Path(upload.filename or "").name
        extension = Path(original_name).suffix.lower()

        if not validate_video_extension(original_name, ALLOWED_EXTENSIONS):
            raise ValueError(
                f"Định dạng video không được hỗ trợ. "
                f"Chỉ chấp nhận: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
            )

        # ── 2. Sinh UUID làm tên file và xác định đường dẫn lưu ──
        video_id = uuid4().hex
        destination = self.settings.upload_dir / f"{video_id}{extension}"

        # ── 3. Đọc và ghi dữ liệu theo chunk ──
        size_bytes = 0
        try:
            with destination.open("wb") as target:
                while chunk := await upload.read(CHUNK_SIZE):
                    size_bytes += len(chunk)

                    # Kiểm tra giới hạn dung lượng
                    if size_bytes > self.settings.max_upload_bytes:
                        raise ValueError(
                            f"Video vượt quá giới hạn dung lượng cho phép "
                            f"({self.settings.max_upload_bytes:,} bytes)."
                        )
                    target.write(chunk)

            # ── 4. Kiểm tra file rỗng ──
            if size_bytes == 0:
                raise ValueError("File video tải lên rỗng, không có dữ liệu.")

            # ── 5. Lưu metadata vào database ──
            logger.info(
                "Đã lưu video: %s -> %s (%d bytes)",
                original_name, destination.name, size_bytes,
            )
            return self.repository.create_video(
                video_id=video_id,
                original_filename=original_name,
                stored_path=destination,
                size_bytes=size_bytes,
            )

        except Exception:
            # ── 6. Dọn dẹp file tạm nếu có lỗi ──
            destination.unlink(missing_ok=True)
            raise

        finally:
            await upload.close()
