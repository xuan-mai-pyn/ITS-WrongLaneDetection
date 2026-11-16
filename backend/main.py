"""
Điểm khởi chạy chính của Backend – FastAPI Application Factory.

File này chịu trách nhiệm:
    - Khởi tạo ứng dụng FastAPI với metadata cho Swagger UI.
    - Đăng ký toàn bộ các nhóm API routes (health, video, detection, violations, statistics).
    - Cấu hình CORS cho phép Frontend giao tiếp với Backend.
    - Thiết lập logging thống nhất cho toàn bộ hệ thống.
    - Mount thư mục static assets (CSS, JS, images) của Frontend.
    - Phục vụ các trang HTML của giao diện người dùng.

Cách chạy:
    python scripts/run_backend.py
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.api.routes import detection, health, statistics, video, violations
from backend.config import Settings, setup_logging

logger = logging.getLogger(__name__)

# ── Đường dẫn thư mục Frontend ──
FRONTEND_DIR = Settings.project_root / "frontend"

# ── Danh sách các trang Frontend hợp lệ ──
VALID_PAGES = {"dashboard", "detection", "history", "statistics"}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Quản lý vòng đời ứng dụng (Application Lifespan).

    Startup (khi server bắt đầu):
        - Thiết lập logging cho toàn hệ thống.
        - Tạo các thư mục lưu trữ cần thiết.
        - Khởi tạo schema database SQLite.
        - Kiểm tra cấu hình và ghi cảnh báo nếu thiếu thành phần.

    Shutdown (khi server tắt):
        - Ghi log thông báo tắt server.
    """
    # ── Startup ──
    setup_logging()
    logger.info("Khởi động ITS Wrong-Lane Detection API...")

    settings: Settings = app.state.settings
    warnings = settings.validate() if hasattr(settings, "validate") else []
    for warning in warnings:
        logger.warning("Cảnh báo cấu hình: %s", warning)

    if not warnings:
        logger.info("Cấu hình hệ thống hợp lệ, sẵn sàng hoạt động.")

    yield

    # ── Shutdown ──
    logger.info("Đã tắt ITS Wrong-Lane Detection API.")


def create_app(settings: Settings | None = None) -> FastAPI:
    """
    Tạo và cấu hình ứng dụng FastAPI.

    Quy trình khởi tạo:
        1. Nạp cấu hình từ Settings (đọc .env).
        2. Tạo các thư mục runtime (uploads, processed, evidence).
        3. Khởi tạo database SQLite và tạo bảng.
        4. Đăng ký middleware CORS.
        5. Đăng ký các nhóm API routes.
        6. Mount thư mục static cho Frontend.
        7. Đăng ký các routes phục vụ trang HTML.

    Args:
        settings: Đối tượng Settings tùy chỉnh (dùng cho testing).
                  Nếu None, tự động tạo Settings từ biến môi trường.

    Returns:
        Đối tượng FastAPI đã cấu hình đầy đủ, sẵn sàng chạy.
    """
    # ── 1. Nạp cấu hình ──
    app_settings = settings or Settings()
    app_settings.prepare_directories()

    # ── 2. Khởi tạo ứng dụng FastAPI ──
    app = FastAPI(
        title="ITS Wrong-Lane Detection API",
        description=(
            "REST API phục vụ hệ thống nhận diện phương tiện đi sai làn đường. "
            "Hỗ trợ upload video, phát hiện và theo dõi phương tiện bằng YOLO + ByteTrack, "
            "xác định vi phạm làn đường dựa trên cấu hình polygon và quy tắc lưu thông."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    # ── 3. Lưu settings và repository vào app.state ──
    app.state.settings = app_settings

    from backend.database.repository import Repository
    app.state.repository = Repository(app_settings.database_path)
    app.state.repository.initialize()

    # ── 4. Cấu hình CORS Middleware ──
    # Cho phép Frontend (có thể chạy trên port khác) gọi API Backend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── 5. Đăng ký các nhóm API routes ──
    app.include_router(health.router, prefix="/api")
    app.include_router(video.router, prefix="/api")
    app.include_router(detection.router, prefix="/api")
    app.include_router(violations.router, prefix="/api")
    app.include_router(statistics.router, prefix="/api")

    # ── 6. Mount thư mục static assets của Frontend ──
    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_DIR / "assets"),
        name="assets",
    )

    # ── 7. Phục vụ các trang HTML của Frontend ──
    @app.get("/", include_in_schema=False)
    def dashboard() -> FileResponse:
        """Trang chủ – chuyển hướng về trang Dashboard."""
        return FileResponse(FRONTEND_DIR / "pages" / "dashboard.html")

    @app.get("/{page_name}", include_in_schema=False)
    def frontend_page(page_name: str) -> FileResponse:
        """
        Phục vụ các trang Frontend theo tên.

        Nếu tên trang không hợp lệ, trả về trang index.html mặc định.
        """
        if page_name in VALID_PAGES:
            return FileResponse(FRONTEND_DIR / "pages" / f"{page_name}.html")
        return FileResponse(FRONTEND_DIR / "index.html")

    return app


# ── Tạo instance ứng dụng mặc định để Uvicorn sử dụng ──
# Lệnh chạy: uvicorn backend.main:app --host 127.0.0.1 --port 8000
app = create_app()
