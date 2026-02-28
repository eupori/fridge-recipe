"""
Meal Plan Service

식단 플래너 CRUD + 장보기 리스트 집계
"""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.meal_plan import MealPlan, MealSlot, MealPlanCreate, MealSlotCreate
from app.models.recommendation import RecommendationRecord, ShoppingItem
from app.services.coupang_service import CoupangLinkService
from app.services.recommendation_service import deduplicate_shopping_list

logger = logging.getLogger(__name__)


class MealPlanService:
    """식단 플래너 서비스"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: UUID, data: MealPlanCreate) -> MealPlan:
        """식단 생성"""
        plan = MealPlan(
            user_id=user_id,
            title=data.title,
            week_start=data.week_start,
        )
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def list_by_user(self, user_id: UUID) -> list[dict]:
        """사용자의 식단 목록 조회"""
        plans = (
            self.db.query(MealPlan)
            .filter(MealPlan.user_id == user_id)
            .order_by(MealPlan.created_at.desc())
            .all()
        )
        return [
            {
                "id": str(p.id),
                "title": p.title,
                "week_start": p.week_start,
                "slot_count": len(p.slots),
                "created_at": p.created_at,
            }
            for p in plans
        ]

    def get(self, plan_id: UUID, user_id: UUID) -> MealPlan | None:
        """식단 상세 조회 (소유자 확인)"""
        return (
            self.db.query(MealPlan)
            .filter(MealPlan.id == plan_id, MealPlan.user_id == user_id)
            .first()
        )

    def delete(self, plan_id: UUID, user_id: UUID) -> bool:
        """식단 삭제 (cascade로 슬롯도 삭제)"""
        plan = self.get(plan_id, user_id)
        if not plan:
            return False
        self.db.delete(plan)
        self.db.commit()
        return True

    def add_slot(self, plan: MealPlan, data: MealSlotCreate) -> MealSlot:
        """슬롯 추가 (같은 요일+식사면 교체)"""
        existing = (
            self.db.query(MealSlot)
            .filter(
                MealSlot.meal_plan_id == plan.id,
                MealSlot.day_of_week == data.day_of_week,
                MealSlot.meal_type == data.meal_type,
            )
            .first()
        )
        if existing:
            existing.recommendation_id = data.recommendation_id
            existing.recipe_index = data.recipe_index
            existing.recipe_title = data.recipe_title
            existing.recipe_image_url = data.recipe_image_url
            self.db.commit()
            self.db.refresh(existing)
            return existing

        slot = MealSlot(
            meal_plan_id=plan.id,
            day_of_week=data.day_of_week,
            meal_type=data.meal_type,
            recommendation_id=data.recommendation_id,
            recipe_index=data.recipe_index,
            recipe_title=data.recipe_title,
            recipe_image_url=data.recipe_image_url,
        )
        self.db.add(slot)
        self.db.commit()
        self.db.refresh(slot)
        return slot

    def remove_slot(self, plan: MealPlan, slot_id: UUID) -> bool:
        """슬롯 제거"""
        slot = (
            self.db.query(MealSlot)
            .filter(MealSlot.id == slot_id, MealSlot.meal_plan_id == plan.id)
            .first()
        )
        if not slot:
            return False
        self.db.delete(slot)
        self.db.commit()
        return True

    def get_shopping_list(self, plan: MealPlan) -> list[ShoppingItem]:
        """식단 전체의 장보기 리스트 집계"""
        all_need: set[str] = set()

        for slot in plan.slots:
            rec = (
                self.db.query(RecommendationRecord)
                .filter(RecommendationRecord.id == slot.recommendation_id)
                .first()
            )
            if not rec:
                continue

            recipes = rec.data.get("recipes", [])
            if slot.recipe_index < len(recipes):
                recipe = recipes[slot.recipe_index]
                all_need.update(recipe.get("ingredients_need", []))

        deduplicated = deduplicate_shopping_list(all_need)
        coupang = CoupangLinkService()
        return [
            ShoppingItem(item=i, purchase_url=coupang.generate_search_url(i))
            for i in deduplicated
        ]
