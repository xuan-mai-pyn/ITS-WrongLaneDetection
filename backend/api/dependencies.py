"""
Khai báo các thành phần phụ thuộc (Dependencies) dùng chung cho các API routes.

File này cung cấp các hàm dependency injection theo mô hình của FastAPI:
    - get_settings: Cung cấp đối tượng Settings quản lý cấu hình.
    - get_repository: Cung cấp đối tượng Repository thao tác cơ sở dữ liệu.
"""

from __future__ import annotations

from fastapi import HTTPException, Request, status

from backend.config import Settings
from backend.database.repository import Repository


def get_settings(request: Request) -> Settings:
    """
    Dependency lấy đối tượng Settings từ trạng thái ứng dụng (app.state).

    Args:
        request: Đối tượng HTTP request hiện tại từ FastAPI.

    Returns:
        Settings: Cấu hình dùng chung của hệ thống.

    Raises:
        HTTPException: Mã 500 khi ứng dụng chưa được nạp cấu hình đúng cách.
    """
    settings = getattr(request.app.state, "settings", None)
    if settings is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cấu hình hệ thống (Settings) chưa được khởi tạo.",
        )
    return settings


def get_repository(request: Request) -> Repository:
    """
    Dependency lấy đối tượng Repository từ trạng thái ứng dụng (app.state).

    Args:
        request: Đối tượng HTTP request hiện tại từ FastAPI.

    Returns:
        Repository: Đối tượng thao tác cơ sở dữ liệu SQLite.

    Raises:
        HTTPException: Mã 500 khi kho lưu trữ dữ liệu chưa sẵn sàng.
    """
    repository = getattr(request.app.state, "repository", None)
    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cơ sở dữ liệu (Repository) chưa được khởi tạo.",
        )
    return repository
