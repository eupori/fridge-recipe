import asyncio
import logging

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.recommendation import RecommendationRecord
from app.services.image_search_service import ImageSearchService

logger = logging.getLogger(__name__)

router = APIRouter()

_image_service: ImageSearchService | None = None


def _get_image_service() -> ImageSearchService:
    global _image_service
    if _image_service is None:
        _image_service = ImageSearchService()
    return _image_service


class BatchImageRequest(BaseModel):
    titles: list[str] = Field(..., min_length=1, max_length=10, description="레시피 제목 목록")
    recommendation_id: str | None = Field(default=None, description="추천 ID (DB 업데이트용)")


class BatchImageItem(BaseModel):
    title: str
    image_url: str | None


class BatchImageResponse(BaseModel):
    images: list[BatchImageItem]


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


@router.post(
    "/batch",
    summary="레시피 이미지 배치 생성",
    description="여러 레시피의 이미지를 병렬로 생성합니다. recommendation_id가 있으면 DB도 업데이트합니다.",
    response_model=BatchImageResponse,
)
async def batch_generate_images(
    request: BatchImageRequest,
    db: Session = Depends(get_db),
):
    service = _get_image_service()

    # 병렬로 이미지 생성
    tasks = [service.get_image(title) for title in request.titles]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    images: list[BatchImageItem] = []
    for title, result in zip(request.titles, results):
        if isinstance(result, Exception):
            logger.error(f"배치 이미지 생성 실패 ({title}): {result}")
            images.append(BatchImageItem(title=title, image_url=None))
        else:
            images.append(BatchImageItem(title=title, image_url=result))

    # recommendation_id가 있으면 DB 업데이트
    if request.recommendation_id:
        try:
            record = (
                db.query(RecommendationRecord)
                .filter(RecommendationRecord.id == request.recommendation_id)
                .first()
            )
            if record and record.data:
                data = dict(record.data)
                recipes = list(data.get("recipes", []))
                updated = False

                # 제목 매칭으로 이미지 URL 업데이트
                image_map = {img.title: img.image_url for img in images if img.image_url}
                for i, recipe in enumerate(recipes):
                    if recipe.get("title") in image_map and not recipe.get("image_url"):
                        recipes[i] = {**recipe, "image_url": image_map[recipe["title"]]}
                        updated = True

                if updated:
                    data["recipes"] = recipes
                    record.data = data
                    db.commit()
                    logger.info(f"DB 이미지 업데이트 완료: {request.recommendation_id}")
        except Exception as e:
            logger.error(f"DB 이미지 업데이트 실패: {e}")

    return BatchImageResponse(images=images)
