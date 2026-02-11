import logging

from fastapi import APIRouter, Query

from app.services.image_search_service import ImageSearchService

logger = logging.getLogger(__name__)

router = APIRouter()

_image_service: ImageSearchService | None = None


def _get_image_service() -> ImageSearchService:
    global _image_service
    if _image_service is None:
        _image_service = ImageSearchService()
    return _image_service


@router.get(
    "/generate",
    summary="레시피 이미지 생성",
    description="레시피 제목으로 이미지를 생성/검색합니다. 캐시가 있으면 즉시 반환됩니다.",
)
async def generate_image(
    title: str = Query(..., description="레시피 제목 (예: 김치볶음밥)"),
):
    service = _get_image_service()
    image_url = await service.get_image(title)

    return {
        "recipe_title": title,
        "image_url": image_url,
    }
