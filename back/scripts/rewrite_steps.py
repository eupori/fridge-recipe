"""
레퍼런스 레시피 조리 단계 리라이팅 스크립트

크롤링한 레시피의 steps를 LLM으로 리라이팅하여 저작권 리스크를 줄인다.
원본은 original_steps 컬럼에 백업한다.

사용법:
    cd back
    PYTHONPATH=. python scripts/rewrite_steps.py              # 전체 (haiku)
    PYTHONPATH=. python scripts/rewrite_steps.py --dry-run     # 5개 미리보기
    PYTHONPATH=. python scripts/rewrite_steps.py --limit 50    # 50개만
    PYTHONPATH=. python scripts/rewrite_steps.py --model sonnet # Sonnet 사용
    PYTHONPATH=. python scripts/rewrite_steps.py --start-id 500 # ID 500부터
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time

# Claude Code 중첩 세션 방지 해제 (이 스크립트는 독립 실행 가능해야 함)
os.environ.pop("CLAUDECODE", None)

from sqlalchemy import inspect, text

from app.core.database import SessionLocal, engine
from app.models.reference_recipe import ReferenceRecipe
from app.services.llm_adapter import _call_claude_cli

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """당신은 한국 요리 레시피 편집자입니다.
주어진 조리 단계를 자연스러운 다른 표현으로 리라이팅하세요.

규칙:
- 각 단계의 의미와 순서를 정확히 보존
- 시간, 불세기, 분량 등 구체적 수치는 그대로 유지
- 표현과 문체만 자연스럽게 변경
- 단계 수를 동일하게 유지
- JSON 배열로만 응답 (설명 없이)"""


def ensure_column_exists():
    """original_steps 컬럼이 없으면 ALTER TABLE로 추가"""
    inspector = inspect(engine)
    columns = [c["name"] for c in inspector.get_columns("reference_recipes")]
    if "original_steps" not in columns:
        logger.info("original_steps 컬럼 추가 중...")
        with engine.begin() as conn:
            dialect = engine.dialect.name
            if dialect == "sqlite":
                conn.execute(text(
                    "ALTER TABLE reference_recipes ADD COLUMN original_steps JSON"
                ))
            else:
                conn.execute(text(
                    "ALTER TABLE reference_recipes ADD COLUMN original_steps JSON DEFAULT NULL"
                ))
        logger.info("original_steps 컬럼 추가 완료")
    else:
        logger.info("original_steps 컬럼 이미 존재")


def build_user_prompt(title: str, steps: list[str]) -> str:
    return f"레시피: {title}\n원본 조리 단계:\n{json.dumps(steps, ensure_ascii=False)}"


def parse_rewritten_steps(response: str) -> list[str]:
    """LLM 응답에서 JSON 배열 파싱"""
    text = response.strip()

    # ```json ... ``` 블록 추출
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        text = text[start:end].strip()

    result = json.loads(text)
    if not isinstance(result, list):
        raise ValueError("응답이 배열이 아닙니다")
    if not all(isinstance(s, str) for s in result):
        raise ValueError("배열 요소가 문자열이 아닙니다")
    return result


def rewrite_recipe(recipe: ReferenceRecipe, model: str, dry_run: bool) -> bool:
    """단일 레시피 리라이팅. 성공 시 True"""
    steps = recipe.steps
    if not steps or not isinstance(steps, list):
        logger.warning(f"  ID={recipe.id} '{recipe.title}': steps가 비어있음, 스킵")
        return False

    user_prompt = build_user_prompt(recipe.title, steps)

    try:
        response = _call_claude_cli(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            model=model,
            timeout=120,
        )
        rewritten = parse_rewritten_steps(response)
    except Exception as e:
        logger.warning(f"  ID={recipe.id} '{recipe.title}': LLM 실패 - {e}")
        return False

    # 검증: 단계 수 ±2 이내
    diff = abs(len(rewritten) - len(steps))
    if diff > 2:
        logger.warning(
            f"  ID={recipe.id} '{recipe.title}': 단계 수 불일치 "
            f"(원본 {len(steps)} → 결과 {len(rewritten)}), 스킵"
        )
        return False

    if dry_run:
        print(f"\n{'='*60}")
        print(f"[ID={recipe.id}] {recipe.title}")
        print(f"{'='*60}")
        for i, (orig, new) in enumerate(zip(steps, rewritten), 1):
            print(f"  {i}. 원본: {orig}")
            print(f"     결과: {new}")
        if len(rewritten) > len(steps):
            for i in range(len(steps), len(rewritten)):
                print(f"  {i+1}. (추가): {rewritten[i]}")
        return True

    # DB 업데이트
    recipe.original_steps = steps
    recipe.steps = rewritten
    return True


def main():
    parser = argparse.ArgumentParser(description="레퍼런스 레시피 조리 단계 리라이팅")
    parser.add_argument("--dry-run", action="store_true", help="5개만 미리보기 (DB 변경 없음)")
    parser.add_argument("--limit", type=int, default=0, help="처리할 최대 개수 (0=전체)")
    parser.add_argument("--model", default="haiku", help="LLM 모델 (haiku/sonnet)")
    parser.add_argument("--start-id", type=int, default=0, help="시작 ID")
    args = parser.parse_args()

    # 컬럼 확인/추가
    ensure_column_exists()

    # 1단계: ID 목록만 빠르게 조회 (세션 즉시 반환)
    db = SessionLocal()
    try:
        query = (
            db.query(ReferenceRecipe.id)
            .filter(ReferenceRecipe.original_steps.is_(None))
            .filter(ReferenceRecipe.steps.isnot(None))
        )
        if args.start_id > 0:
            query = query.filter(ReferenceRecipe.id >= args.start_id)
        query = query.order_by(ReferenceRecipe.id)

        if args.dry_run:
            ids = [r.id for r in query.limit(5).all()]
        elif args.limit > 0:
            ids = [r.id for r in query.limit(args.limit).all()]
        else:
            ids = [r.id for r in query.all()]
    finally:
        db.close()

    total = len(ids)
    if total == 0:
        logger.info("리라이팅할 레시피가 없습니다 (모두 완료되었거나 조건에 맞는 레시피 없음)")
        return

    logger.info(f"리라이팅 대상: {total}개 (모델: {args.model}, dry-run: {args.dry_run})")

    success = 0
    fail = 0
    start_time = time.time()

    try:
        for i, recipe_id in enumerate(ids, 1):
            # 2단계: 레시피마다 새 세션 (장시간 연결 유지 방지)
            db = SessionLocal()
            try:
                recipe = db.get(ReferenceRecipe, recipe_id)
                if recipe is None or recipe.original_steps is not None:
                    # 이미 처리됨 (다른 프로세스 등)
                    continue

                ok = rewrite_recipe(recipe, model=args.model, dry_run=args.dry_run)
                if ok:
                    success += 1
                    if not args.dry_run:
                        db.commit()
                else:
                    fail += 1
            except Exception as e:
                logger.warning(f"  ID={recipe_id}: DB 오류 - {e}")
                fail += 1
            finally:
                try:
                    db.close()
                except Exception:
                    pass  # 이미 끊긴 연결 무시

            # 10개마다 진행상황 로깅
            if i % 10 == 0 or i == total:
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                logger.info(
                    f"진행: {i}/{total} ({i*100//total}%) | "
                    f"성공: {success} | 실패: {fail} | "
                    f"속도: {rate:.1f}개/초 | "
                    f"경과: {elapsed:.0f}초"
                )

        logger.info(f"\n완료! 성공: {success}, 실패: {fail}, 총: {total}")

    except KeyboardInterrupt:
        logger.info("\n중단됨 (Ctrl+C). 이미 커밋된 레시피는 저장되어 있습니다.")


if __name__ == "__main__":
    main()
