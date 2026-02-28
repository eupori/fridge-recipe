"""
Meal Plan API endpoints

- POST /meal-plans - 식단 생성
- GET /meal-plans - 내 식단 목록
- GET /meal-plans/{plan_id} - 식단 상세
- DELETE /meal-plans/{plan_id} - 식단 삭제
- POST /meal-plans/{plan_id}/slots - 슬롯 추가/교체
- DELETE /meal-plans/{plan_id}/slots/{slot_id} - 슬롯 제거
- GET /meal-plans/{plan_id}/shopping-list - 장보기 리스트
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.meal_plan import (
    MealPlanCreate,
    MealPlanListItem,
    MealPlanResponse,
    MealSlotCreate,
    MealSlotResponse,
)
from app.models.user import User
from app.services.auth_service import get_current_user
from app.services.meal_plan_service import MealPlanService

router = APIRouter()


@router.post("", response_model=MealPlanResponse)
def create_meal_plan(
    data: MealPlanCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """식단 생성"""
    service = MealPlanService(db)
    plan = service.create(current_user.id, data)
    return MealPlanResponse(
        id=str(plan.id),
        title=plan.title,
        week_start=plan.week_start,
        slots=[],
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


@router.get("", response_model=list[MealPlanListItem])
def list_meal_plans(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """내 식단 목록"""
    service = MealPlanService(db)
    return service.list_by_user(current_user.id)


@router.get("/{plan_id}", response_model=MealPlanResponse)
def get_meal_plan(
    plan_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """식단 상세 조회 (슬롯 포함)"""
    service = MealPlanService(db)
    plan = service.get(plan_id, current_user.id)
    if not plan:
        raise HTTPException(status_code=404, detail="식단을 찾을 수 없습니다.")
    return MealPlanResponse(
        id=str(plan.id),
        title=plan.title,
        week_start=plan.week_start,
        slots=[
            MealSlotResponse(
                id=str(s.id),
                day_of_week=s.day_of_week,
                meal_type=s.meal_type,
                recommendation_id=s.recommendation_id,
                recipe_index=s.recipe_index,
                recipe_title=s.recipe_title,
                recipe_image_url=s.recipe_image_url,
            )
            for s in plan.slots
        ],
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


@router.delete("/{plan_id}")
def delete_meal_plan(
    plan_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """식단 삭제"""
    service = MealPlanService(db)
    if not service.delete(plan_id, current_user.id):
        raise HTTPException(status_code=404, detail="식단을 찾을 수 없습니다.")
    return {"detail": "삭제되었습니다."}


@router.post("/{plan_id}/slots", response_model=MealSlotResponse)
def add_meal_slot(
    plan_id: UUID,
    data: MealSlotCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """슬롯 추가/교체 (같은 요일+식사 타입이면 교체)"""
    service = MealPlanService(db)
    plan = service.get(plan_id, current_user.id)
    if not plan:
        raise HTTPException(status_code=404, detail="식단을 찾을 수 없습니다.")
    slot = service.add_slot(plan, data)
    return MealSlotResponse(
        id=str(slot.id),
        day_of_week=slot.day_of_week,
        meal_type=slot.meal_type,
        recommendation_id=slot.recommendation_id,
        recipe_index=slot.recipe_index,
        recipe_title=slot.recipe_title,
        recipe_image_url=slot.recipe_image_url,
    )


@router.delete("/{plan_id}/slots/{slot_id}")
def remove_meal_slot(
    plan_id: UUID,
    slot_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """슬롯 제거"""
    service = MealPlanService(db)
    plan = service.get(plan_id, current_user.id)
    if not plan:
        raise HTTPException(status_code=404, detail="식단을 찾을 수 없습니다.")
    if not service.remove_slot(plan, slot_id):
        raise HTTPException(status_code=404, detail="슬롯을 찾을 수 없습니다.")
    return {"detail": "삭제되었습니다."}


@router.get("/{plan_id}/shopping-list")
def get_shopping_list(
    plan_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """식단 전체 장보기 리스트"""
    service = MealPlanService(db)
    plan = service.get(plan_id, current_user.id)
    if not plan:
        raise HTTPException(status_code=404, detail="식단을 찾을 수 없습니다.")
    return service.get_shopping_list(plan)
