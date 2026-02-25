"""만개의레시피 크롤러 — JSON-LD 파싱 + HTML 폴백"""
from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.crawl_utils import (
    CATEGORY_MAP,
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
PAGES_PER_CATEGORY = 8


# ── 리스트 페이지 ──────────────────────────────────────────


def get_recipe_ids_from_list(
    cat_id: int, page: int, client: httpx.Client
) -> list[str]:
    """리스트 페이지에서 레시피 ID 추출"""
    url = f"{BASE_URL}/recipe/list.html"
    params = {"cat4": cat_id, "order": "reco", "page": page}

    try:
        resp = client.get(url, params=params)
        resp.raise_for_status()
    except Exception as e:
        logger.warning(f"리스트 페이지 실패: cat={cat_id}, page={page}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    ids: list[str] = []

    for link in soup.select("a.common_sp_link"):
        href = link.get("href", "")
        match = re.search(r"/recipe/(\d+)", href)
        if match:
            ids.append(match.group(1))

    return ids


# ── JSON-LD / HTML 파싱 ──────────────────────────────────────


def parse_iso_duration(duration: str | None) -> int | None:
    """ISO 8601 duration → 분 (예: PT15M → 15, PT1H30M → 90)"""
    if not duration:
        return None
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?", duration)
    if not match:
        return None
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    return hours * 60 + minutes if (hours or minutes) else None


def parse_recipe_jsonld(soup: BeautifulSoup) -> dict | None:
    """JSON-LD에서 레시피 데이터 추출"""
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                data = data[0]
            if data.get("@type") == "Recipe":
                return data
        except (json.JSONDecodeError, TypeError):
            continue
    return None


def parse_recipe_html(soup: BeautifulSoup) -> dict | None:
    """HTML 셀렉터로 레시피 데이터 추출 (JSON-LD 폴백)"""
    title_el = soup.select_one("div.view2_summary h3")
    if not title_el:
        return None

    title = title_el.get_text(strip=True)

    ingredients: list[str] = []
    for li in soup.select("div.ready_ingre3 ul li"):
        name_el = li.select_one("a")
        if name_el:
            ingredients.append(name_el.get_text(strip=True))

    steps: list[str] = []
    for step_div in soup.select("div.view_step div.view_step_cont"):
        text = step_div.get_text(strip=True)
        if text:
            steps.append(text)

    if not ingredients or not steps:
        return None

    return {
        "name": title,
        "recipeIngredient": ingredients,
        "recipeInstructions": [{"text": s} for s in steps],
    }


def parse_view_count(soup: BeautifulSoup) -> int:
    """조회수 추출"""
    view_el = soup.select_one("span.hit")
    if view_el:
        text = view_el.get_text(strip=True).replace(",", "")
        match = re.search(r"\d+", text)
        if match:
            return int(match.group())
    return 0


def parse_rating(soup: BeautifulSoup) -> int | None:
    """평점 추출 (0-50 스케일)"""
    rating_el = soup.select_one("div.view2_summary_star span.star_score")
    if rating_el:
        text = rating_el.get_text(strip=True)
        try:
            return int(float(text) * 10)
        except ValueError:
            pass
    return None


def parse_servings(text: str | None) -> int | None:
    """인분 파싱"""
    if not text:
        return None
    match = re.search(r"(\d+)", str(text))
    return int(match.group(1)) if match else None


# ── 개별 레시피 크롤링 ──────────────────────────────────────


def crawl_recipe(
    recipe_id: str, cat_id: int, client: httpx.Client
) -> dict | None:
    """개별 레시피 페이지 크롤링"""
    url = f"{BASE_URL}/recipe/{recipe_id}"
    category = CATEGORY_MAP.get(cat_id, "반찬단품")

    try:
        resp = client.get(url)
        resp.raise_for_status()
    except Exception as e:
        logger.warning(f"레시피 페이지 실패: {recipe_id}: {e}")
        return None

    soup = BeautifulSoup(resp.text, "lxml")

    # JSON-LD 우선
    jsonld = parse_recipe_jsonld(soup)
    if not jsonld:
        jsonld = parse_recipe_html(soup)
    if not jsonld:
        logger.debug(f"파싱 실패: {recipe_id}")
        return None

    title = (jsonld.get("name") or "").strip()
    if not title:
        return None

    # 재료
    all_ingredients = jsonld.get("recipeIngredient", [])
    if isinstance(all_ingredients, str):
        all_ingredients = [all_ingredients]
    all_ingredients = [ing.strip() for ing in all_ingredients if ing.strip()]
    if not all_ingredients:
        return None

    # 조리 단계
    instructions = jsonld.get("recipeInstructions", [])
    steps: list[str] = []
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

    time_min = parse_iso_duration(
        jsonld.get("totalTime") or jsonld.get("cookTime")
    )
    servings = parse_servings(jsonld.get("recipeYield"))
    key_ingredients = extract_key_ingredients(all_ingredients)
    technique = generate_technique_heuristic(steps)
    view_count = parse_view_count(soup)
    rating = parse_rating(soup)

    return {
        "title": title,
        "category": category,
        "key_ingredients": key_ingredients,
        "all_ingredients": all_ingredients,
        "steps": steps,
        "technique": technique,
        "time_min": time_min,
        "servings": servings,
        "source": "만개의레시피",
        "source_url": url,
        "view_count": view_count,
        "rating": rating,
    }


# ── 메인 ──────────────────────────────────────────


def crawl_10000recipe() -> int:
    """만개의레시피 크롤링 실행. 저장된 레시피 수 반환."""
    db = get_session()
    saved_count = 0

    with httpx.Client(
        headers=HEADERS, timeout=10.0, follow_redirects=True
    ) as client:
        for cat_id, cat_name in CATEGORY_MAP.items():
            logger.info(f"카테고리 크롤링 시작: {cat_name} (cat4={cat_id})")

            for page in range(1, PAGES_PER_CATEGORY + 1):
                recipe_ids = get_recipe_ids_from_list(cat_id, page, client)
                if not recipe_ids:
                    logger.info(
                        f"  페이지 {page}: 레시피 없음, 다음 카테고리로"
                    )
                    break

                logger.info(
                    f"  페이지 {page}: {len(recipe_ids)}개 레시피 발견"
                )

                for rid in recipe_ids:
                    polite_delay(1.0, 2.5)
                    data = crawl_recipe(rid, cat_id, client)
                    if data and save_recipe(db, data):
                        saved_count += 1
                        if saved_count % 50 == 0:
                            logger.info(f"  저장 진행: {saved_count}개")

                polite_delay(1.5, 3.0)

    db.close()
    logger.info(f"만개의레시피 크롤링 완료: {saved_count}개 저장")
    return saved_count


if __name__ == "__main__":
    crawl_10000recipe()
