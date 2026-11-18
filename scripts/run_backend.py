"""
Script khởi chạy Backend server trong quá trình phát triển.

Giúp đơn giản hóa thao tác chạy máy chủ: thay vì gõ lệnh uvicorn dài,
chỉ cần chạy: python scripts/run_backend.py

Script sẽ:
    1. Thêm thư mục gốc dự án vào sys.path để import được package backend.
    2. Đọc cấu hình host và port từ Settings (file .env).
    3. Khởi động Uvicorn server phục vụ ứng dụng FastAPI.
"""

import sys
from pathlib import Path

# Thêm thư mục gốc dự án (thư mục cha của scripts/) vào đường dẫn tìm kiếm module
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uvicorn

from backend.config import Settings

if __name__ == "__main__":
    settings = Settings()
    print(f"Khởi động ITS Wrong-Lane Detection API tại http://{settings.host}:{settings.port}")
    print(f"Swagger UI: http://{settings.host}:{settings.port}/docs")
    print(f"Dashboard:  http://{settings.host}:{settings.port}/")
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )
