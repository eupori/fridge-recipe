#!/usr/bin/env python3
"""확장 크롤링 스크립트 — 대량 레퍼런스 레시피 수집

사용법:
    cd back

    # 1. 카테고리 확장 크롤링 (16개 카테고리 x 25페이지, ~5000개 목표)
    PYTHONPATH=. python scripts/crawl_expand.py

    # 2. 목표 개수 지정
    PYTHONPATH=. python scripts/crawl_expand.py --target 10000

    # 3. 순차 ID 크롤링 (가장 빠름, 카테고리 자동 분류)
    PYTHONPATH=. python scripts/crawl_expand.py --mode sequential

    # 4. 카테고리 + 순차 둘 다
    PYTHONPATH=. python scripts/crawl_expand.py --mode both

    # 5. YouTube 포함 (브라우저 쿠키 필요)
    PYTHONPATH=. python scripts/crawl_expand.py --youtube --cookies ~/cookies.txt

    # 6. 현재 DB 상태 확인
    PYTHONPATH=. python scripts/crawl_expand.py --stats

    # 7. 딜레이/페이지 수 조정
    PYTHONPATH=. python scripts/crawl_expand.py --pages 30 --delay 0.5

YouTube 쿠키 준비:
    1. Chrome에서 youtube.com 로그인
    2. 확장프로그램 'Get cookies.txt LOCALLY' 설치
    3. youtube.com에서 쿠키 내보내기 → ~/cookies.txt 저장
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func

from app.core.database import SessionLocal, create_tables
from app.models.reference_recipe import ReferenceRecipe
from scripts.crawl_utils import (
    extract_key_ingredients,
    generate_technique_heuristic,
    get_session,
    polite_delay,
    save_recipe,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

BASE_URL = "https://www.10000recipe.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
}

# ── 확장 카테고리 매핑 (16개) ──────────────────────────────

EXPANDED_CATEGORIES: dict[int, str] = {
    # 기존 6개 (이미 크롤링됨, 추가 페이지/정렬로 확장)
    52: "밥",
    53: "면분식",
    54: "국물",
    55: "국물",
    56: "반찬단품",
    63: "반찬단품",
    # 신규 10개
    57: "반찬단품",    # 김치
    58: "반찬단품",    # 젓갈
    59: "반찬단품",    # 양념/장류
    60: "양식",        # 양식
    61: "아시안",      # 중식/일식
    64: "간식",        # 디저트
    65: "퓨전",        # 퓨전
    66: "면분식",      # 분식
    68: "안주",        # 안주
    69: "간식",        # 간식/디저트
}

# 정렬 옵션 (다양한 레시피 발굴)
SORT_ORDERS = ["reco", "hit", "scrap"]

# 순차 모드 카테고리 자동 분류 키워드
CATEGORY_KEYWORDS = {
    "국물": ["국", "탕", "찌개", "수프", "스프", "죽", "전골"],
    "밥": ["밥", "덮밥", "볶음밥", "비빔밥", "주먹밥", "리조또"],
    "면분식": ["면", "국수", "파스타", "라면", "떡볶이", "분식", "우동", "소바",
               "냉면", "짜장", "짬뽕", "만두", "토스트", "샌드위치", "빵"],
    "간식": ["케이크", "쿠키", "디저트", "떡", "과자", "빵", "머핀", "타르트"],
    "양식": ["스테이크", "그라탕", "리조또", "피자", "버거", "오믈렛"],
    "안주": ["안주", "꼬치", "튀김"],
}


# ══════════════════════════════════════════════════════════
# 만개의레시피 — 공통 파싱
# ══════════════════════════════════════════════════════════


def parse_iso_duration(duration: str | None) -> int | None:
    if not duration:
        return None
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?", duration)
    if not match:
        return None
    h, m = int(match.group(1) or 0), int(match.group(2) or 0)
    return h * 60 + m if (h or m) else None


def parse_recipe_page(html: str) -> dict | None:
    """레시피 페이지 HTML → 데이터 dict (JSON-LD 우선, HTML 폴백)"""
    soup = BeautifulSoup(html, "lxml")

    # JSON-LD 파싱
    jsonld = None
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                data = data[0]
            if data.get("@type") == "Recipe":
                jsonld = data
                break
        except (json.JSONDecodeError, TypeError):
            continue

    # HTML 폴백
    if not jsonld:
        title_el = soup.select_one("div.view2_summary h3")
        if not title_el:
            return None

        ingredients = []
        for li in soup.select("div.ready_ingre3 ul li"):
            name_el = li.select_one("a")
            if name_el:
                ingredients.append(name_el.get_text(strip=True))

        steps = []
        for step_div in soup.select("div.view_step div.view_step_cont"):
            text = step_div.get_text(strip=True)
            if text:
                steps.append(text)

        if not ingredients or not steps:
            return None

        jsonld = {
            "name": title_el.get_text(strip=True),
            "recipeIngredient": ingredients,
            "recipeInstructions": [{"text": s} for s in steps],
        }

    title = (jsonld.get("name") or "").strip()
    if not title:
        return None

    all_ingredients = jsonld.get("recipeIngredient", [])
    if isinstance(all_ingredients, str):
        all_ingredients = [all_ingredients]
    all_ingredients = [i.strip() for i in all_ingredients if i.strip()]
    if not all_ingredients:
        return None

    instructions = jsonld.get("recipeInstructions", [])
    steps = []
    for inst in instructions:
        if isinstance(inst, dict):
            text = inst.get("text", "").strip()
        elif isinstance(inst, str):
            text = inst.strip()
        else:
            continue
        if text:
            steps.append(text)
    if not steps:
        return None

    # 조회수
    view_count = 0
    view_el = soup.select_one("span.hit")
    if view_el:
        text = view_el.get_text(strip=True).replace(",", "")
        m = re.search(r"\d+", text)
        if m:
            view_count = int(m.group())

    # 평점
    rating = None
    rating_el = soup.select_one("div.view2_summary_star span.star_score")
    if rating_el:
        try:
            rating = int(float(rating_el.get_text(strip=True)) * 10)
        except ValueError:
            pass

    # 인분
    servings = None
    yield_text = jsonld.get("recipeYield")
    if yield_text:
        m = re.search(r"(\d+)", str(yield_text))
        if m:
            servings = int(m.group(1))

    return {
        "title": title,
        "all_ingredients": all_ingredients,
        "steps": steps,
        "key_ingredients": extract_key_ingredients(all_ingredients),
        "technique": generate_technique_heuristic(steps),
        "time_min": parse_iso_duration(
            jsonld.get("totalTime") or jsonld.get("cookTime")
        ),
        "servings": servings,
        "view_count": view_count,
        "rating": rating,
    }


def classify_category(title: str, ingredients: list[str]) -> str:
    """제목 + 재료 키워드로 카테고리 자동 분류"""
    text = (title + " " + " ".join(ingredients)).lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return category
    return "반찬단품"


# ══════════════════════════════════════════════════════════
# 모드 1: 카테고리 확장 크롤링
# ══════════════════════════════════════════════════════════


def crawl_category_mode(
    db, client: httpx.Client, target: int, pages_per_cat: int, delay: float
) -> int:
    """카테고리별 리스트 → 개별 레시피 크롤링"""
    saved = 0

    for sort_order in SORT_ORDERS:
        if saved >= target:
            break

        for cat_id, cat_name in EXPANDED_CATEGORIES.items():
            if saved >= target:
                break

            logger.info(
                f"[카테고리] {cat_name} (cat4={cat_id}, "
                f"정렬={sort_order}, {saved}/{target})"
            )

            for page in range(1, pages_per_cat + 1):
                if saved >= target:
                    break

                # 리스트 페이지
                polite_delay(delay, delay * 2)
                try:
                    resp = client.get(
                        f"{BASE_URL}/recipe/list.html",
                        params={
                            "cat4": cat_id,
                            "order": sort_order,
                            "page": page,
                        },
                    )
                    resp.raise_for_status()
                except Exception as e:
                    logger.warning(f"  리스트 실패: page={page}: {e}")
                    break

                soup = BeautifulSoup(resp.text, "lxml")
                ids = []
                for link in soup.select("a.common_sp_link"):
                    href = link.get("href", "")
                    m = re.search(r"/recipe/(\d+)", href)
                    if m:
                        ids.append(m.group(1))

                if not ids:
                    break

                logger.info(f"  페이지 {page}: {len(ids)}개 발견")

                for rid in ids:
                    if saved >= target:
                        break

                    url = f"{BASE_URL}/recipe/{rid}"
                    polite_delay(delay, delay * 1.5)

                    try:
                        r = client.get(url)
                        r.raise_for_status()
                    except Exception:
                        continue

                    data = parse_recipe_page(r.text)
                    if not data:
                        continue

                    data.update({
                        "category": cat_name,
                        "source": "만개의레시피",
                        "source_url": url,
                    })

                    if save_recipe(db, data):
                        saved += 1
                        if saved % 100 == 0:
                            logger.info(f"  ✓ 저장 진행: {saved}/{target}")

    return saved


# ══════════════════════════════════════════════════════════
# 모드 2: 순차 ID 크롤링 (가장 빠름)
# ══════════════════════════════════════════════════════════


def crawl_sequential_mode(
    db, client: httpx.Client, target: int, delay: float,
    start_id: int = 7080000,
) -> int:
    """최신 레시피 ID부터 역순으로 크롤링"""
    saved = 0
    not_found_streak = 0
    max_streak = 200  # 연속 200개 404 → 중단

    current_id = start_id
    logger.info(
        f"[순차] ID {current_id}부터 역순 크롤링 시작 (목표: {target})"
    )

    while saved < target and current_id > 0 and not_found_streak < max_streak:
        url = f"{BASE_URL}/recipe/{current_id}"
        polite_delay(delay * 0.5, delay)

        try:
            resp = client.get(url)
        except Exception:
            current_id -= 1
            not_found_streak += 1
            continue

        if resp.status_code == 404 or resp.status_code >= 400:
            current_id -= 1
            not_found_streak += 1
            continue

        not_found_streak = 0
        data = parse_recipe_page(resp.text)
        if not data:
            current_id -= 1
            continue

        # 카테고리 자동 분류
        category = classify_category(
            data["title"], data["all_ingredients"]
        )
        data.update({
            "category": category,
            "source": "만개의레시피",
            "source_url": url,
        })

        if save_recipe(db, data):
            saved += 1
            if saved % 100 == 0:
                logger.info(
                    f"  ✓ 순차 진행: {saved}/{target} "
                    f"(현재 ID: {current_id})"
                )

        current_id -= 1

    if not_found_streak >= max_streak:
        logger.info(f"  연속 {max_streak}개 미발견 → 순차 모드 종료")

    return saved


# ══════════════════════════════════════════════════════════
# YouTube 크롤링 (쿠키 지원)
# ══════════════════════════════════════════════════════════

YOUTUBE_CHANNELS = [
    {"name": "백종원", "id": "UCyn-K7rZLXjGl7VXGweIlcA", "source": "youtube_백종원"},
    {"name": "류수영", "id": "UCW_FCSKNI4kO57dBVLFMJYQ", "source": "youtube_류수영"},
    {"name": "이밥차", "id": "UCjFJlMGPaiWP8DNoxzF2YuA", "source": "youtube_이밥차"},
    {"name": "자취요리신", "id": "UC6-BVff4BPBqxNsAEYxfVbg", "source": "youtube_자취요리신"},
    {"name": "승우아빠", "id": "UC7M-Wz4zK8oikt6ATcoTZBQ", "source": "youtube_승우아빠"},
]


def crawl_youtube(cookies_path: str, target: int = 300) -> int:
    """YouTube 셰프 채널 크롤링 (쿠키 인증)"""
    from youtube_transcript_api import YouTubeTranscriptApi

    api_key = os.environ.get("YOUTUBE_API_KEY", "")
    if not api_key:
        logger.warning("YOUTUBE_API_KEY 없음 → YouTube 건너뜀")
        return 0

    # 쿠키 지원 초기화
    try:
        ytt = YouTubeTranscriptApi(cookie_path=cookies_path)
        logger.info(f"YouTube 쿠키 로드: {cookies_path}")
    except Exception:
        try:
            ytt = YouTubeTranscriptApi(cookies=cookies_path)
        except Exception:
            ytt = YouTubeTranscriptApi()
            logger.warning("쿠키 없이 YouTube 접근 (IP 차단될 수 있음)")

    db = get_session()
    saved = 0

    for ch in YOUTUBE_CHANNELS:
        if saved >= target:
            break

        logger.info(f"[YouTube] {ch['name']} 채널 크롤링")

        # 영상 목록 가져오기
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(
                    "https://www.googleapis.com/youtube/v3/search",
                    params={
                        "key": api_key,
                        "channelId": ch["id"],
                        "part": "snippet",
                        "type": "video",
                        "order": "viewCount",
                        "maxResults": 50,
                    },
                )
                resp.raise_for_status()
                videos = [
                    {
                        "id": item["id"]["videoId"],
                        "title": item["snippet"]["title"],
                    }
                    for item in resp.json().get("items", [])
                    if item.get("id", {}).get("videoId")
                ]
        except Exception as e:
            logger.warning(f"  영상 목록 실패: {e}")
            continue

        logger.info(f"  {len(videos)}개 영상 발견")

        for video in videos:
            if saved >= target:
                break

            video_url = f"https://www.youtube.com/watch?v={video['id']}"

            # 자막 추출
            try:
                fetched = ytt.fetch(video["id"], languages=["ko"])
                transcript = " ".join(s.text for s in fetched)
            except Exception:
                continue

            if not transcript or len(transcript) < 100:
                continue

            polite_delay(0.5, 1.0)

            # Haiku 구조화
            structured = _structure_with_haiku(transcript, video["title"])
            if not structured:
                continue

            key_ings = extract_key_ingredients(structured["all_ingredients"])
            data = {
                "title": structured["title"],
                "category": structured.get("category", "반찬단품"),
                "key_ingredients": key_ings,
                "all_ingredients": structured["all_ingredients"],
                "steps": structured["steps"],
                "technique": None,
                "time_min": structured.get("time_min"),
                "servings": structured.get("servings"),
                "source": ch["source"],
                "source_url": video_url,
                "view_count": 0,
                "rating": None,
            }

            if save_recipe(db, data):
                saved += 1
                logger.info(f"  ✓ {structured['title']}")

    db.close()
    return saved


def _structure_with_haiku(transcript: str, title: str) -> dict | None:
    """Claude Haiku로 자막 → 구조화 JSON"""
    prompt = (
        "다음 요리 영상 자막에서 레시피를 추출하여 JSON으로 반환.\n\n"
        f"제목: {title}\n자막:\n{transcript[:3000]}\n\n"
        'JSON 형식만 (설명 없이):\n'
        '{"title":"제목","category":"밥/국물/반찬단품/면분식 중 하나",'
        '"all_ingredients":["재료 분량"],"steps":["단계"],'
        '"time_min":숫자,"servings":숫자}\n\n'
        "레시피 아니면 null"
    )
    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--model", "haiku"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return None
        output = result.stdout.strip()
        if output.lower() == "null" or not output:
            return None
        output = re.sub(r"^```(?:json)?\n?", "", output)
        output = re.sub(r"\n?```$", "", output)
        data = json.loads(output)
        if not data.get("title") or not data.get("all_ingredients"):
            return None
        valid_cats = {"밥", "국물", "반찬단품", "면분식"}
        if data.get("category") not in valid_cats:
            data["category"] = "반찬단품"
        return data
    except Exception:
        return None


# ══════════════════════════════════════════════════════════
# 통계 / 유틸
# ══════════════════════════════════════════════════════════


def print_stats() -> None:
    """현재 DB 레퍼런스 레시피 통계"""
    db = SessionLocal()
    total = db.query(ReferenceRecipe).count()

    print(f"\n{'=' * 55}")
    print(f"  레퍼런스 레시피 DB 현황")
    print(f"{'=' * 55}")
    print(f"  총 레시피: {total:,}개\n")

    print("  [카테고리별]")
    for cat, cnt in (
        db.query(ReferenceRecipe.category, func.count())
        .group_by(ReferenceRecipe.category)
        .order_by(func.count().desc())
        .all()
    ):
        bar = "█" * (cnt // 50)
        print(f"    {cat:<8} {cnt:>5}개  {bar}")

    print("\n  [소스별]")
    for source, cnt in (
        db.query(ReferenceRecipe.source, func.count())
        .group_by(ReferenceRecipe.source)
        .order_by(func.count().desc())
        .all()
    ):
        print(f"    {source:<20} {cnt:>5}개")

    # 평균 조회수 상위 카테고리
    print("\n  [평균 조회수 상위 레시피]")
    top = (
        db.query(ReferenceRecipe)
        .order_by(ReferenceRecipe.view_count.desc())
        .limit(5)
        .all()
    )
    for r in top:
        print(
            f"    {r.title[:30]:<30} "
            f"조회수: {r.view_count:>10,}"
        )

    print(f"\n{'=' * 55}\n")
    db.close()


# ══════════════════════════════════════════════════════════
# 메인
# ══════════════════════════════════════════════════════════


def main() -> None:
    parser = argparse.ArgumentParser(
        description="확장 레퍼런스 레시피 크롤링",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--target", type=int, default=5000,
        help="목표 저장 개수 (기본: 5000)",
    )
    parser.add_argument(
        "--mode", choices=["category", "sequential", "both"],
        default="category",
        help="크롤링 모드 (기본: category)",
    )
    parser.add_argument(
        "--pages", type=int, default=25,
        help="카테고리당 페이지 수 (기본: 25)",
    )
    parser.add_argument(
        "--delay", type=float, default=0.8,
        help="요청 간 최소 딜레이 초 (기본: 0.8)",
    )
    parser.add_argument(
        "--start-id", type=int, default=7080000,
        help="순차 모드 시작 ID (기본: 7080000)",
    )
    parser.add_argument(
        "--youtube", action="store_true",
        help="YouTube 셰프 크롤링 활성화",
    )
    parser.add_argument(
        "--cookies", type=str, default="",
        help="YouTube 쿠키 파일 경로 (예: ~/cookies.txt)",
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="현재 DB 통계만 출력하고 종료",
    )

    args = parser.parse_args()

    create_tables()

    if args.stats:
        print_stats()
        return

    # 현재 DB 상태
    db_before = SessionLocal()
    before_count = db_before.query(ReferenceRecipe).count()
    db_before.close()

    print(f"\n{'=' * 55}")
    print(f"  확장 크롤링 시작")
    print(f"  현재 DB: {before_count:,}개 / 목표: +{args.target:,}개")
    print(f"  모드: {args.mode} / 딜레이: {args.delay}s")
    print(f"{'=' * 55}\n")

    start_time = time.monotonic()
    total_saved = 0
    db = get_session()

    with httpx.Client(
        headers=HEADERS, timeout=10.0, follow_redirects=True
    ) as client:
        remaining = args.target

        # 카테고리 모드
        if args.mode in ("category", "both"):
            logger.info("━━━ 카테고리 확장 크롤링 시작 ━━━")
            n = crawl_category_mode(
                db, client, remaining, args.pages, args.delay
            )
            total_saved += n
            remaining -= n
            logger.info(f"카테고리 모드 완료: {n}개 저장")

        # 순차 모드
        if args.mode in ("sequential", "both") and remaining > 0:
            logger.info("━━━ 순차 ID 크롤링 시작 ━━━")
            n = crawl_sequential_mode(
                db, client, remaining, args.delay, args.start_id
            )
            total_saved += n
            remaining -= n
            logger.info(f"순차 모드 완료: {n}개 저장")

    db.close()

    # YouTube
    if args.youtube and remaining > 0:
        logger.info("━━━ YouTube 셰프 크롤링 시작 ━━━")
        n = crawl_youtube(args.cookies, min(remaining, 300))
        total_saved += n
        logger.info(f"YouTube 완료: {n}개 저장")

    elapsed = time.monotonic() - start_time
    elapsed_min = elapsed / 60

    print(f"\n{'=' * 55}")
    print(f"  크롤링 완료!")
    print(f"  신규 저장: {total_saved:,}개 ({elapsed_min:.1f}분)")
    print(f"  총 DB: {before_count + total_saved:,}개")
    print(f"{'=' * 55}")

    print_stats()


if __name__ == "__main__":
    main()
