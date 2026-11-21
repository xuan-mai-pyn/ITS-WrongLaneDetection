"""
Script dòng lệnh độc lập khởi tạo cơ sở dữ liệu và thư mục lưu trữ cho dự án.


Cách chạy:
    python scripts/setup_database.py
"""

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Thêm thư mục gốc của dự án vào đường dẫn tìm kiếm module Python
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config import Settings
from backend.database.connection import connect, initialize_database


def setup() -> None:
    """Thực thi toàn bộ quy trình thiết lập cơ sở dữ liệu và thư mục."""
    print("=" * 65)
    print("  ITS WRONG-LANE DETECTION - DATABASE SETUP")
    print("  SQLite database and storage setup")
    print("=" * 65)

    settings = Settings()

    # 1. Tạo các thư mục lưu trữ
    print("\n[1/3] Đang kiểm tra và tạo thư mục lưu trữ...")
    settings.prepare_directories()
    for directory in (settings.upload_dir, settings.processed_dir, settings.evidence_dir):
        print(f"  + Thư mục sẵn sàng: {directory}")

    # 2. Khởi tạo cấu trúc bảng SQLite
    print(f"\n[2/3] Đang khởi tạo cơ sở dữ liệu tại: {settings.database_path}...")
    initialize_database(settings.database_path)

    # 3. Kiểm tra và xác nhận các bảng đã tạo thành công
    print("\n[3/3] Đang xác thực các bảng dữ liệu...")
    with connect(settings.database_path) as connection:
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
        ).fetchall()
        table_names = [row["name"] for row in tables]
        for name in table_names:
            count = connection.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            print(f"  + Bảng '{name}': Đã sẵn sàng ({count} bản ghi hiện có)")

        indexes = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
        ).fetchall()
        print(f"\n  + Tổng số chỉ mục (Indexes) đã thiết lập: {len(indexes)}")

    print("\n" + "=" * 65)
    print("  THIẾT LẬP HOÀN TẤT! HỆ THỐNG SẴN SÀNG KHỞI CHẠY BACKEND.")
    print(f"  Lệnh chạy server: python scripts/run_backend.py")
    print("=" * 65)


if __name__ == "__main__":
    setup()
