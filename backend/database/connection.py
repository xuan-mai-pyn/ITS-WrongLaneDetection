"""
Quản lý kết nối cơ sở dữ liệu SQLite và khởi tạo cấu trúc bảng (Schema).

Module này chịu trách nhiệm:
    - Quản lý vòng đời kết nối SQLite thông qua Context Manager `connect()`.
    - Kích hoạt chế độ WAL (Write-Ahead Logging) giúp đọc/ghi đồng thời tốc độ cao,
      tránh hiện tượng khóa cơ sở dữ liệu (Database Locked) khi video đang xử lý ngầm.
    - Thực thi toàn vẹn dữ liệu quan hệ bằng khóa ngoại (PRAGMA foreign_keys = ON).
    - Định nghĩa cấu trúc 3 bảng cốt lõi:
        + `videos`: Lưu trữ metadata của các tệp video tải lên và kết quả tổng hợp.
        + `detection_tasks`: Quản lý tiến trình xử lý nhận diện (progress, status).
        + `violations`: Lưu trữ chi tiết từng hành vi phương tiện đi sai làn đường.
    - Cung cấp hàm `initialize_database()` tự động tạo bảng và di chuyển dữ liệu (migration).
"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)

# ── Định nghĩa cấu trúc Schema cơ sở dữ liệu quan hệ SQLite ──
SCHEMA = """
-- 1. Bảng lưu trữ thông tin video tải lên và kết quả phân tích
CREATE TABLE IF NOT EXISTS videos (
    id TEXT PRIMARY KEY,
    original_filename TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    uploaded_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'uploaded',
    processing_seconds REAL,
    vehicle_type_counts_json TEXT NOT NULL DEFAULT '{}',
    processed_frames INTEGER NOT NULL DEFAULT 0,
    vehicle_count INTEGER NOT NULL DEFAULT 0,
    violation_count INTEGER NOT NULL DEFAULT 0
);

-- 2. Bảng theo dõi tiến trình của các tác vụ nhận diện ngầm
CREATE TABLE IF NOT EXISTS detection_tasks (
    id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    progress INTEGER NOT NULL DEFAULT 0,
    current_frame INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    result_json TEXT,
    output_path TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 3. Bảng lưu trữ hồ sơ chi tiết các phương tiện vi phạm làn đường
CREATE TABLE IF NOT EXISTS violations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL REFERENCES detection_tasks(id) ON DELETE CASCADE,
    video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    track_id INTEGER NOT NULL,
    vehicle_type TEXT NOT NULL DEFAULT 'unknown',
    source_lane TEXT NOT NULL,
    destination_lane TEXT NOT NULL,
    frame_index INTEGER NOT NULL,
    timestamp_seconds REAL NOT NULL,
    detected_at TEXT NOT NULL,
    evidence_path TEXT
);

-- 4. Tạo các chỉ mục (Indexes) để tăng tốc độ truy vấn tìm kiếm
CREATE INDEX IF NOT EXISTS idx_tasks_video_id ON detection_tasks(video_id);
CREATE INDEX IF NOT EXISTS idx_violations_video_id ON violations(video_id);
CREATE INDEX IF NOT EXISTS idx_violations_task_id ON violations(task_id);
CREATE INDEX IF NOT EXISTS idx_violations_detected_at ON violations(detected_at DESC);
"""


@contextmanager
def connect(database_path: Path) -> Iterator[sqlite3.Connection]:
    """
    Mở và đóng kết nối cơ sở dữ liệu SQLite an toàn theo mô hình Context Manager.

    Tính năng nổi bật:
        - timeout=30: Tránh lỗi timeout khi nhiều tác vụ đồng thời truy xuất.
        - row_factory = sqlite3.Row: Cho phép truy cập dữ liệu cột theo tên trường như Dictionary.
        - PRAGMA foreign_keys = ON: Đảm bảo toàn vẹn dữ liệu quan hệ giữa các bảng.
        - PRAGMA journal_mode = WAL: Tối ưu hóa ghi nhật ký trước (Write-Ahead Logging)
          cho phép đọc và ghi dữ liệu đồng thời mà không bị khóa (non-blocking).
        - PRAGMA synchronous = NORMAL: Cân bằng tối ưu giữa hiệu năng và độ an toàn đĩa.
        - Tự động gọi connection.commit() khi hoàn thành và connection.rollback() nếu có lỗi.

    Args:
        database_path: Đường dẫn tệp SQLite trên ổ đĩa.

    Yields:
        sqlite3.Connection: Đối tượng kết nối đang hoạt động.
    """
    connection = sqlite3.connect(database_path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = NORMAL")
    try:
        yield connection
        connection.commit()
    except BaseException as exc:
        connection.rollback()
        logger.error("Lỗi giao dịch cơ sở dữ liệu, thực hiện rollback: %s", exc)
        raise
    finally:
        connection.close()


def initialize_database(database_path: Path) -> None:
    """
    Khởi tạo toàn bộ cấu trúc bảng và chỉ mục cho cơ sở dữ liệu SQLite.

    Quy trình:
        1. Đảm bảo thư mục cha chứa file cơ sở dữ liệu đã tồn tại trên đĩa.
        2. Thực thi toàn bộ đoạn mã DDL trong biến SCHEMA.
        3. Kiểm tra tính tương thích các cột dữ liệu (Auto-migration):
           Tự động bổ sung các cột processing_seconds hoặc vehicle_type_counts_json
           nếu cơ sở dữ liệu được tạo từ các phiên bản trước đó.

    Args:
        database_path: Đường dẫn tới file cơ sở dữ liệu SQLite.
    """
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with connect(database_path) as connection:
        connection.executescript(SCHEMA)

        # ── Kiểm tra và tự động cập nhật cấu trúc bảng videos (Migration) ──
        video_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(videos)").fetchall()
        }
        if "processing_seconds" not in video_columns:
            connection.execute("ALTER TABLE videos ADD COLUMN processing_seconds REAL")
            logger.info("Đã bổ sung cột processing_seconds vào bảng videos.")

        if "vehicle_type_counts_json" not in video_columns:
            connection.execute(
                "ALTER TABLE videos ADD COLUMN vehicle_type_counts_json TEXT NOT NULL DEFAULT '{}'"
            )
            logger.info("Đã bổ sung cột vehicle_type_counts_json vào bảng videos.")

        violation_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(violations)"
            ).fetchall()
        }
        if "vehicle_type" not in violation_columns:
            connection.execute(
                "ALTER TABLE violations ADD COLUMN vehicle_type TEXT NOT NULL DEFAULT 'unknown'"
            )
            logger.info("Đã bổ sung cột vehicle_type vào bảng violations.")

    logger.info("Khởi tạo cơ sở dữ liệu thành công tại: %s", database_path)
