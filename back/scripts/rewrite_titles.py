"""
레퍼런스 레시피 제목 정리 스크립트

크롤링 원본 제목에서 [태그], 홍보성 문구, 따옴표, 이모지 등을 제거하여
깔끔한 레시피 제목으로 리라이팅한다.
원본은 original_title 컬럼에 백업한다.

사용법:
    cd back
    PYTHONPATH=. python scripts/rewrite_titles.py              # 전체 (haiku)
    PYTHONPATH=. python scripts/rewrite_titles.py --dry-run     # 10개 미리보기
    PYTHONPATH=. python scripts/rewrite_titles.py --limit 50    # 50개만
    PYTHONPATH=. python scripts/rewrite_titles.py --model sonnet # Sonnet 사용
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time

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
주어진 레시피 제목들을 깔끔하게 정리하세요.

규칙:
- [태그], #해시태그, ♥♡❤️ 이모지, 느낌표 과다 사용 제거
- "초간단", "꿀팁", "밥도둑", "존맛", "인생" 등 홍보성/감탄성 수식어 제거
- 따옴표(작은따옴표, 큰따옴표) 제거
- "만들기", "만드는 법", "레시피", "만드는법" 등 불필요한 접미사 제거
- "백종원", "서가앤쿡" 등 출처/인물명 제거
- 핵심 요리명만 남기기 (예: "김치볶음밥", "된장찌개", "파채무침")
- 조리법이 제목에 포함된 경우 유지 (예: "소고기 미역국" → 그대로)
- 20자 이내로 간결하게
- 한국어만 사용 (영어 병기 제거)
- JSON 배열로만 응답 (입력 순서 유지, 설명 없이)

예시:
입력: ["[간단 자취요리] 꿀팁공유 고깃집 밥도둑! 고깃집 된장찌개 만들기", "내 인생 레시피,친정 엄마표 \\"파채무침\\""]
출력: ["고깃집 된장찌개", "파채무침"]"""


def needs_cleanup(title: str) -> bool:
    """제목이 정리 필요한지 판단"""
    patterns = [
        r'\[.*?\]',           # [태그]
        r'[♥♡❤️🔥✨💕]',     # 이모지
        r'["\'\u201c\u201d]', # 따옴표
        r'!!+',               # 느낌표 2개 이상
        r'#\S+',              # 해시태그
    ]
    keywords = [
        '꿀팁', '인생', '밥도둑', '초간단', '존맛', '꿀맛', '만들기',
        '만드는 법', '만드는법', '레시피', '비법', '황금', '만능',
        '백종원', '레알', '갓', 'No.', 'EP.',
    ]

    for p in patterns:
        if re.search(p, title):
            return True
    for kw in keywords:
        if kw in title:
            return True
    if len(title) > 25:
        return True
    return False


def ensure_column_exists():
    """original_title 컬럼이 없으면 ALTER TABLE로 추가"""
    inspector = inspect(engine)
    columns = [c["name"] for c in inspector.get_columns("reference_recipes")]
    if "original_title" not in columns:
        logger.info("original_title 컬럼 추가 중...")
        with engine.begin() as conn:
            dialect = engine.dialect.name
            if dialect == "sqlite":
                conn.execute(text(
                    "ALTER TABLE reference_recipes ADD COLUMN original_title TEXT"
                ))
            else:
                conn.execute(text(
                    "ALTER TABLE reference_recipes ADD COLUMN original_title TEXT DEFAULT NULL"
                ))
        logger.info("original_title 컬럼 추가 완료")
    else:
        logger.info("original_title 컬럼 이미 존재")


def parse_titles(response: str) -> list[str]:
    """LLM 응답에서 JSON 배열 파싱"""
    text = response.strip()
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


def main():
    parser = argparse.ArgumentParser(description="레퍼런스 레시피 제목 정리")
    parser.add_argument("--dry-run", action="store_true", help="10개만 미리보기")
    parser.add_argument("--limit", type=int, default=0, help="처리할 최대 개수")
    parser.add_argument("--model", default="haiku", help="LLM 모델 (haiku/sonnet)")
    parser.add_argument("--batch-size", type=int, default=20, help="배치 크기")
    args = parser.parse_args()

    ensure_column_exists()

    # 정리 필요한 레시피 조회
    db = SessionLocal()
    try:
        recipes = (
            db.query(ReferenceRecipe.id, ReferenceRecipe.title)
            .filter(ReferenceRecipe.original_title.is_(None))
            .order_by(ReferenceRecipe.id)
            .all()
        )
        # 정리 필요한 것만 필터
        targets = [(r.id, r.title) for r in recipes if needs_cleanup(r.title)]
    finally:
        db.close()

    if args.dry_run:
        targets = targets[:10]
    elif args.limit > 0:
        targets = targets[:args.limit]

    total = len(targets)
    if total == 0:
        logger.info("정리할 제목이 없습니다.")
        return

    logger.info(f"정리 대상: {total}개 (모델: {args.model}, 배치: {args.batch_size}개씩)")

    success = 0
    fail = 0
    start_time = time.time()

    try:
        for batch_start in range(0, total, args.batch_size):
            batch = targets[batch_start:batch_start + args.batch_size]
            batch_ids = [b[0] for b in batch]
            batch_titles = [b[1] for b in batch]

            user_prompt = f"다음 레시피 제목들을 정리해주세요:\n{json.dumps(batch_titles, ensure_ascii=False)}"

            try:
                response = _call_claude_cli(
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    model=args.model,
                    timeout=120,
                )
                cleaned = parse_titles(response)
            except Exception as e:
                logger.warning(f"  배치 {batch_start}-{batch_start+len(batch)}: LLM 실패 - {e}")
                fail += len(batch)
                continue

            if len(cleaned) != len(batch):
                logger.warning(
                    f"  배치 {batch_start}: 개수 불일치 "
                    f"(입력 {len(batch)} → 출력 {len(cleaned)}), 스킵"
                )
                fail += len(batch)
                continue

            if args.dry_run:
                for orig, new in zip(batch_titles, cleaned):
                    changed = "✓" if orig != new else "="
                    print(f"  {changed} {orig}")
                    if orig != new:
                        print(f"    → {new}")
                success += len(batch)
                continue

            # DB 업데이트
            db = SessionLocal()
            try:
                for recipe_id, orig_title, new_title in zip(batch_ids, batch_titles, cleaned):
                    recipe = db.get(ReferenceRecipe, recipe_id)
                    if recipe and recipe.original_title is None:
                        recipe.original_title = orig_title
                        recipe.title = new_title
                db.commit()
                success += len(batch)
            except Exception as e:
                logger.warning(f"  배치 {batch_start}: DB 오류 - {e}")
                db.rollback()
                fail += len(batch)
            finally:
                db.close()

            # 진행상황
            done = batch_start + len(batch)
            elapsed = time.time() - start_time
            rate = done / elapsed if elapsed > 0 else 0
            logger.info(
                f"진행: {done}/{total} ({done*100//total}%) | "
                f"성공: {success} | 실패: {fail} | "
                f"속도: {rate:.1f}개/초 | 경과: {elapsed:.0f}초"
            )

        logger.info(f"\n완료! 성공: {success}, 실패: {fail}, 총: {total}")

    except KeyboardInterrupt:
        logger.info("\n중단됨 (Ctrl+C). 이미 커밋된 변경은 저장되어 있습니다.")


if __name__ == "__main__":
    main()
