"""
API endpoint truy xuất danh sách Vi phạm làn đường (Violations).

Cung cấp endpoint REST:
    - GET /api/violations : Lấy danh sách các trường hợp vi phạm đã ghi nhận.

Frontend sử dụng endpoint này để hiển thị trang Lịch sử vi phạm (History).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from backend.api.dependencies import get_repository
from backend.database.repository import Repository
from backend.schemas.violation import ViolationRead

router = APIRouter(prefix="/violations", tags=["violations"])


@router.get(
    "",
    response_model=list[ViolationRead],
    summary="Lấy danh sách vi phạm",
    description=(
        "Trả về danh sách các trường hợp phương tiện đi sai làn đường "
        "đã được hệ thống ghi nhận, sắp xếp theo thời gian mới nhất. "
        "Mỗi bản ghi bao gồm thông tin xe vi phạm (track_id), "
        "làn xuất phát, làn vi phạm, thời điểm trong video và đường dẫn ảnh bằng chứng."
    ),
)
def list_violations(
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
        description="Số lượng bản ghi tối đa trả về (1 - 500, mặc định 100)",
    ),
    repository: Repository = Depends(get_repository),
) -> list[ViolationRead]:
    """
    Truy vấn danh sách vi phạm từ database.

    Args:
        limit: Giới hạn số bản ghi trả về.
        repository: Đối tượng Repository (tự động inject qua FastAPI Depends).

    Returns:
        Danh sách các bản ghi vi phạm, sắp xếp theo detected_at giảm dần.
    """
    return repository.list_violations(limit=limit)
