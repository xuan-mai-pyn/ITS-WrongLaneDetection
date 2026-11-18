"""
Các hàm tiện ích hỗ trợ quản lý và xử lý file trong hệ thống.

Cung cấp các chức năng:
    - ensure_parent: Đảm bảo thư mục cha tồn tại trước khi ghi file.
    - validate_video_extension: Kiểm tra đuôi file video hợp lệ.
    - sanitize_filename: Chuẩn hóa tên file an toàn, loại bỏ ký tự lạ.
    - format_bytes: Chuyển đổi dung lượng byte sang KB, MB, GB dễ đọc.
    - safe_delete: Xóa file an toàn mà không làm sập chương trình.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Tập hợp định dạng video mặc định được hệ thống chấp nhận ──
DEFAULT_ALLOWED_EXTENSIONS = frozenset({".mp4", ".avi", ".mov", ".mkv"})


def ensure_parent(path: Path) -> Path:
    """
    Đảm bảo thư mục cha của đường dẫn đã tồn tại trước khi ghi file.

    Nếu thư mục cha chưa có, hàm sẽ tự động tạo thư mục kèm tất cả các cấp cha.

    Args:
        path: Đường dẫn file cần tạo hoặc ghi.

    Returns:
        Path: Chính đối tượng path ban đầu.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def validate_video_extension(
    filename: str,
    allowed_extensions: set[str] | frozenset[str] | None = None,
) -> bool:
    """
    Kiểm tra phần mở rộng (đuôi file) của video có thuộc danh sách hợp lệ hay không.

    Args:
        filename: Tên file hoặc đường dẫn file cần kiểm tra.
        allowed_extensions: Tập các đuôi file cho phép (mặc định: mp4, avi, mov, mkv).

    Returns:
        bool: True nếu đuôi file hợp lệ, ngược lại False.
    """
    allowed = allowed_extensions or DEFAULT_ALLOWED_EXTENSIONS
    suffix = Path(filename).suffix.lower()
    return suffix in allowed


def sanitize_filename(filename: str) -> str:
    """
    Chuẩn hóa tên file để đảm bảo an toàn khi lưu vào hệ thống tệp.

    Loại bỏ các ký tự có thể gây lỗi đường dẫn hoặc lỗ hổng bảo mật:
        - Giữ lại các chữ cái, số, dấu gạch dưới (_), gạch ngang (-) và dấu chấm (.).
        - Thay thế khoảng trắng và ký tự đặc biệt bằng dấu gạch dưới.

    Args:
        filename: Tên file gốc ban đầu.

    Returns:
        str: Tên file đã được chuẩn hóa an toàn.
    """
    clean_name = Path(filename).name
    # Thay thế các ký tự không an toàn thành dấu gạch dưới
    clean_name = re.sub(r"[^\w\.\-]", "_", clean_name)
    # Loại bỏ các dấu gạch dưới liên tiếp
    clean_name = re.sub(r"_+", "_", clean_name)
    return clean_name or "uploaded_video"


def format_bytes(size_bytes: int) -> str:
    """
    Chuyển đổi kích thước tính bằng byte sang chuỗi thân thiện với người dùng (KB, MB, GB).

    Ví dụ:
        format_bytes(1048576) -> "1.0 MB"
        format_bytes(52428800) -> "50.0 MB"

    Args:
        size_bytes: Dung lượng file theo byte.

    Returns:
        str: Chuỗi dung lượng đã định dạng kèm đơn vị.
    """
    if size_bytes < 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0 or unit == "TB":
            return f"{size_bytes:.1f} {unit}" if unit != "B" else f"{size_bytes} B"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def safe_delete(path: Path) -> bool:
    """
    Xóa một file trên đĩa một cách an toàn.

    Không gây lỗi exception nếu file không tồn tại hoặc gặp lỗi cấp quyền.

    Args:
        path: Đường dẫn file cần xóa.

    Returns:
        bool: True nếu xóa thành công, False nếu file không tồn tại hoặc lỗi.
    """
    try:
        if path.is_file():
            path.unlink(missing_ok=True)
            logger.debug("Đã xóa file: %s", path)
            return True
        return False
    except OSError as exc:
        logger.warning("Không thể xóa file %s: %s", path, exc)
        return False
