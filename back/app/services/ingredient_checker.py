"""
LLM 기반 재료 검증 — Claude CLI(Haiku)를 사용하여 식재료 여부 판별

블록리스트로 잡히지 않는 비식품(자동차, 컴퓨터, 의자 등)을 감지한다.
Haiku 모델을 사용하여 1-2초 내에 응답.
"""

from __future__ import annotations

import asyncio
import json
import logging

from app.services.llm_adapter import _call_claude_cli

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """당신은 식재료 검증기입니다.

사용자가 입력한 항목 목록에서 사람이 먹을 수 없는 것을 골라내세요.

식재료 O: 채소, 과일, 고기, 생선, 해산물, 유제품, 곡물, 양념, 조미료, 가공식품, 음료, 견과류, 허브, 식용유, 소스 등
식재료 X: 사물, 기계, 도구, 가구, 동물(비식용), 장소, 사람 이름, 추상적 개념, 브랜드명(식품 브랜드 제외) 등

주의 - 한국 요리 용어를 도구/사물과 혼동하지 마세요:
- 대패삼겹, 대패삼겹살 → 식재료 O (얇게 썬 삼겹살, 도구 아님)
- 칼국수 → 식재료 O (면 요리, 칼이 아님)
- 돌솥밥 → 식재료 O (돌솥에 지은 밥)
- 철판볶음 → 식재료 O (철판에 볶은 요리)

응답: JSON만 출력
{"non_food": ["비식재료1", "비식재료2"]}

모두 식재료이면:
{"non_food": []}"""


async def check_ingredients_with_llm(ingredients: list[str]) -> list[str]:
    """
    LLM(Haiku)으로 재료가 실제 식재료인지 검증.

    Returns:
        비식재료로 판별된 항목 목록 (비어 있으면 모두 통과)
    """
    if not ingredients:
        return []

    items_str = ", ".join(ingredients)
    user_prompt = f"다음 항목들이 식재료인지 판별: {items_str}"

    try:
        content = await asyncio.to_thread(
            _call_claude_cli,
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            model="haiku",
            timeout=15,
        )

        # JSON 파싱
        content = content.strip()
        if "```" in content:
            start = content.find("```json")
            if start == -1:
                start = content.find("```")
            start = content.find("\n", start) + 1
            end = content.find("```", start)
            content = content[start:end].strip()

        result = json.loads(content)
        non_food = result.get("non_food", [])

        if non_food:
            logger.info(f"LLM 재료 검증: 비식재료 감지 {non_food}")
        else:
            logger.info("LLM 재료 검증: 모두 식재료 통과")

        return non_food

    except Exception as e:
        logger.warning(f"LLM 재료 검증 실패 (통과 처리): {e}")
        return []
