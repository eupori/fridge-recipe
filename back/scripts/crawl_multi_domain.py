#!/usr/bin/env python3
"""다중 도메인 + YouTube 레시피 수집기

목표:
- 여러 레시피 사이트의 JSON-LD Recipe를 범용 파싱
- YouTube 요리 채널의 자막을 LLM으로 구조화
- 공통 스키마(JSONL)로 저장

출력 스키마:
{
  "title": "김치찌개",
  "category": "국물",
  "key_ingredients": ["김치", "돼지고기", "두부"],
  "all_ingredients": ["김치 200g", "돼지고기 150g", "두부 1/2모"],
  "steps": ["김치를 볶는다", "물을 붓고 끓인다"],
  "technique": "센불에서 김치를 먼저 볶기",
  "time_min": 15,
  "servings": 2,
  "source": "만개의레시피",
  "source_url": "https://example.com/recipe/123",
  "view_count": 50000,
  "rating": 45
}
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from xml.etree import ElementTree

import httpx
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.crawl_utils import extract_key_ingredients, generate_technique_heuristic, polite_delay
from scripts.crawl_youtube_chefs import (  # 재사용
    CHEF_CHANNELS,
    get_channel_videos,
    get_transcript,
    structure_with_haiku,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.7,en;q=0.6",
}

VALID_CATEGORIES = {"밥", "국물", "반찬단품", "면분식", "양식", "아시안", "퓨전", "안주", "간식"}


@dataclass(frozen=True)
class DomainConfig:
    key: str
    source: str
    sitemap_urls: tuple[str, ...]
    include_patterns: tuple[str, ...] = tuple()


DOMAIN_CONFIGS: dict[str, DomainConfig] = {
    # 이미 만개의레시피가 있어도 옵션으로 포함 가능
    "10000recipe": DomainConfig(
        key="10000recipe",
        source="만개의레시피",
        sitemap_urls=("https://www.10000recipe.com/rss/recipe.xml",),
        include_patterns=("/recipe/",),
    ),
    "allrecipes": DomainConfig(
        key="allrecipes",
        source="allrecipes",
        sitemap_urls=(
            "https://www.allrecipes.com/sitemaps/",
            "https://www.allrecipes.com/sitemap.xml",
        ),
        include_patterns=("/recipe/",),
    ),
    "maangchi": DomainConfig(
        key="maangchi",
        source="maangchi",
        sitemap_urls=("https://www.maangchi.com/sitemap_index.xml",),
    ),
    "mykoreankitchen": DomainConfig(
        key="mykoreankitchen",
        source="mykoreankitchen",
        sitemap_urls=("https://mykoreankitchen.com/sitemap_index.xml",),
    ),
    "koreanbapsang": DomainConfig(
        key="koreanbapsang",
        source="koreanbapsang",
        sitemap_urls=("https://www.koreanbapsang.com/sitemap_index.xml",),
    ),
    "seriouseats": DomainConfig(
        key="seriouseats",
        source="seriouseats",
        sitemap_urls=("https://www.seriouseats.com/sitemap.xml",),
        include_patterns=("/",),
    ),
}


def flatten_jsonld(blob: Any) -> list[dict[str, Any]]:
    """JSON-LD blob에서 Recipe 후보 dict 목록 추출"""
    out: list[dict[str, Any]] = []

    def _walk(node: Any) -> None:
        if isinstance(node, list):
            for item in node:
                _walk(item)
            return
        if not isinstance(node, dict):
            return

        node_type = node.get("@type")
        if isinstance(node_type, list):
            is_recipe = "Recipe" in node_type
        else:
            is_recipe = node_type == "Recipe"

        if is_recipe:
            out.append(node)

        graph = node.get("@graph")
        if graph:
            _walk(graph)

    _walk(blob)
    return out


def parse_jsonld_recipes(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    recipes: list[dict[str, Any]] = []

    for script in soup.find_all("script", type="application/ld+json"):
        text = (script.string or script.get_text() or "").strip()
        if not text:
            continue

        text = text.replace("\u0000", "")
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue

        recipes.extend(flatten_jsonld(data))

    return recipes


def parse_time_minutes(value: Any) -> int | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?", text)
    if m:
        h = int(m.group(1) or 0)
        mins = int(m.group(2) or 0)
        total = h * 60 + mins
        return total if total > 0 else None

    # "45 min", "1 hour 20 minutes" 같은 문자열 처리
    hour = re.search(r"(\d+)\s*(h|hr|hour|hours|시간)", text, flags=re.I)
    minute = re.search(r"(\d+)\s*(m|min|mins|minute|minutes|분)", text, flags=re.I)
    total = 0
    if hour:
        total += int(hour.group(1)) * 60
    if minute:
        total += int(minute.group(1))

    if total > 0:
        return total

    direct = re.search(r"(\d+)", text)
    return int(direct.group(1)) if direct else None


def parse_servings(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, list) and value:
        value = value[0]

    m = re.search(r"(\d+)", str(value))
    return int(m.group(1)) if m else None


def parse_instructions(raw: Any) -> list[str]:
    steps: list[str] = []

    def _append(text: str) -> None:
        t = re.sub(r"\s+", " ", text).strip()
        if t:
            steps.append(t)

    if isinstance(raw, str):
        _append(raw)
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                _append(item)
            elif isinstance(item, dict):
                if isinstance(item.get("text"), str):
                    _append(item["text"])
                elif isinstance(item.get("name"), str):
                    _append(item["name"])
                elif isinstance(item.get("itemListElement"), list):
                    for sub in item["itemListElement"]:
                        if isinstance(sub, dict) and isinstance(sub.get("text"), str):
                            _append(sub["text"])
    elif isinstance(raw, dict):
        if isinstance(raw.get("text"), str):
            _append(raw["text"])

    return steps


def normalize_category(title: str, raw_category: Any, ingredients: list[str]) -> str:
    raw = ""
    if isinstance(raw_category, list):
        raw = " ".join(str(x) for x in raw_category)
    elif raw_category is not None:
        raw = str(raw_category)

    text = f"{title} {raw} {' '.join(ingredients)}".lower()

    if any(k in text for k in ["찌개", "국", "탕", "스프", "soup", "stew", "broth"]):
        return "국물"
    if any(k in text for k in ["밥", "리조또", "볶음밥", "rice", "risotto"]):
        return "밥"
    if any(k in text for k in ["면", "파스타", "라면", "국수", "noodle", "pasta"]):
        return "면분식"
    if any(k in text for k in ["dessert", "cake", "cookie", "디저트", "간식", "베이킹"]):
        return "간식"
    if any(k in text for k in ["안주", "술", "beer", "pub", "snack"]):
        return "안주"
    if any(k in text for k in ["chinese", "japanese", "thai", "asian", "일식", "중식"]):
        return "아시안"
    if any(k in text for k in ["western", "italian", "french", "양식"]):
        return "양식"
    if any(k in text for k in ["fusion", "퓨전"]):
        return "퓨전"
    return "반찬단품"


def parse_rating(raw_recipe: dict[str, Any]) -> int | None:
    agg = raw_recipe.get("aggregateRating")
    if isinstance(agg, dict):
        value = agg.get("ratingValue")
        if value is not None:
            try:
                v = float(value)
                if 0 <= v <= 5:
                    return int(round(v * 10))
                if 0 <= v <= 100:
                    return int(round(v))
            except (TypeError, ValueError):
                pass
    return None


def parse_view_count(raw_recipe: dict[str, Any]) -> int:
    stats = raw_recipe.get("interactionStatistic")
    if isinstance(stats, dict):
        stats = [stats]

    if isinstance(stats, list):
        for st in stats:
            if not isinstance(st, dict):
                continue
            count = st.get("userInteractionCount")
            if count is None:
                continue
            try:
                return int(float(str(count).replace(",", "")))
            except ValueError:
                continue
    return 0


def normalize_recipe(raw_recipe: dict[str, Any], source: str, source_url: str) -> dict[str, Any] | None:
    title = str(raw_recipe.get("name") or "").strip()
    if not title:
        return None

    all_ingredients = raw_recipe.get("recipeIngredient") or []
    if isinstance(all_ingredients, str):
        all_ingredients = [all_ingredients]
    all_ingredients = [str(x).strip() for x in all_ingredients if str(x).strip()]
    if not all_ingredients:
        return None

    steps = parse_instructions(raw_recipe.get("recipeInstructions"))
    if not steps:
        return None

    time_min = parse_time_minutes(raw_recipe.get("totalTime") or raw_recipe.get("cookTime"))
    servings = parse_servings(raw_recipe.get("recipeYield"))
    rating = parse_rating(raw_recipe)
    view_count = parse_view_count(raw_recipe)

    category = normalize_category(title, raw_recipe.get("recipeCategory"), all_ingredients)
    if category not in VALID_CATEGORIES:
        category = "반찬단품"

    return {
        "title": title,
        "category": category,
        "key_ingredients": extract_key_ingredients(all_ingredients),
        "all_ingredients": all_ingredients,
        "steps": steps,
        "technique": generate_technique_heuristic(steps),
        "time_min": time_min,
        "servings": servings,
        "source": source,
        "source_url": source_url,
        "view_count": view_count,
        "rating": rating,
    }


def fetch_xml(client: httpx.Client, url: str) -> str | None:
    try:
        resp = client.get(url, timeout=20)
        if resp.status_code >= 400:
            return None
        return resp.text
    except Exception:
        return None


def parse_sitemap_urls(xml_text: str) -> tuple[list[str], list[str]]:
    """(sub_sitemap_urls, page_urls)"""
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return [], []

    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0] + "}"

    submaps: list[str] = []
    pages: list[str] = []

    if root.tag.endswith("sitemapindex"):
        for sm in root.findall(f"{ns}sitemap"):
            loc = sm.find(f"{ns}loc")
            if loc is not None and loc.text:
                submaps.append(loc.text.strip())
    elif root.tag.endswith("urlset"):
        for u in root.findall(f"{ns}url"):
            loc = u.find(f"{ns}loc")
            if loc is not None and loc.text:
                pages.append(loc.text.strip())

    return submaps, pages


def discover_urls_from_sitemaps(
    client: httpx.Client,
    config: DomainConfig,
    limit: int,
) -> list[str]:
    seen_sitemaps: set[str] = set()
    queue: list[str] = list(config.sitemap_urls)
    urls: list[str] = []
    seen_urls: set[str] = set()

    while queue and len(urls) < limit * 3:
        sitemap_url = queue.pop(0)
        if sitemap_url in seen_sitemaps:
            continue
        seen_sitemaps.add(sitemap_url)

        xml_text = fetch_xml(client, sitemap_url)
        if not xml_text:
            continue

        submaps, page_urls = parse_sitemap_urls(xml_text)
        for sm in submaps:
            if sm not in seen_sitemaps:
                queue.append(sm)

        for page_url in page_urls:
            if page_url in seen_urls:
                continue
            if config.include_patterns and not any(p in page_url for p in config.include_patterns):
                continue

            seen_urls.add(page_url)
            urls.append(page_url)
            if len(urls) >= limit * 3:
                break

    return urls


def crawl_domain(client: httpx.Client, config: DomainConfig, limit: int, delay: float) -> list[dict[str, Any]]:
    logger.info("[%s] URL 탐색 시작", config.key)
    page_urls = discover_urls_from_sitemaps(client, config, limit=limit)
    logger.info("[%s] 후보 URL %d개 발견", config.key, len(page_urls))

    results: list[dict[str, Any]] = []
    seen_fingerprint: set[str] = set()

    for idx, url in enumerate(page_urls, 1):
        if len(results) >= limit:
            break

        polite_delay(delay * 0.6, delay)

        try:
            resp = client.get(url, timeout=20)
            if resp.status_code >= 400:
                continue
        except Exception:
            continue

        recipes = parse_jsonld_recipes(resp.text)
        if not recipes:
            continue

        chosen = None
        for raw in recipes:
            normalized = normalize_recipe(raw, source=config.source, source_url=url)
            if normalized:
                chosen = normalized
                break

        if not chosen:
            continue

        fp = f"{chosen['title'].strip().lower()}|{'/'.join(chosen['key_ingredients'][:3]).lower()}"
        if fp in seen_fingerprint:
            continue
        seen_fingerprint.add(fp)

        results.append(chosen)

        if len(results) % 50 == 0:
            logger.info("[%s] 진행 %d/%d (URL %d 처리)", config.key, len(results), limit, idx)

    logger.info("[%s] 완료: %d개", config.key, len(results))
    return results


def crawl_youtube(max_per_channel: int, delay: float) -> list[dict[str, Any]]:
    api_key = os.environ.get("YOUTUBE_API_KEY", "")
    if not api_key:
        logger.warning("YOUTUBE_API_KEY 미설정: YouTube 수집 건너뜀")
        return []

    out: list[dict[str, Any]] = []

    for chef in CHEF_CHANNELS:
        logger.info("[youtube] 채널: %s", chef["name"])
        videos = get_channel_videos(chef["channel_id"], api_key, max_per_channel)
        logger.info("[youtube] %s 영상 %d개", chef["name"], len(videos))

        for video in videos:
            transcript = get_transcript(video["video_id"])
            if not transcript:
                continue

            polite_delay(delay * 0.5, delay)
            structured = structure_with_haiku(transcript, video["title"])
            if not structured:
                continue

            all_ingredients = [str(x).strip() for x in structured.get("all_ingredients", []) if str(x).strip()]
            steps = [str(x).strip() for x in structured.get("steps", []) if str(x).strip()]
            if not all_ingredients or not steps:
                continue

            category = structured.get("category", "반찬단품")
            if category not in VALID_CATEGORIES:
                category = "반찬단품"

            out.append({
                "title": structured.get("title") or video["title"],
                "category": category,
                "key_ingredients": extract_key_ingredients(all_ingredients),
                "all_ingredients": all_ingredients,
                "steps": steps,
                "technique": generate_technique_heuristic(steps),
                "time_min": structured.get("time_min"),
                "servings": structured.get("servings"),
                "source": chef["source_prefix"],
                "source_url": f"https://www.youtube.com/watch?v={video['video_id']}",
                "view_count": 0,
                "rating": None,
            })

    logger.info("[youtube] 완료: %d개", len(out))
    return out


def unique_by_source_url(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in items:
        src = item.get("source_url", "")
        if not src or src in seen:
            continue
        seen.add(src)
        out.append(item)
    return out


def parse_domain_list(raw: str) -> list[str]:
    if not raw or raw.strip() == "all":
        return list(DOMAIN_CONFIGS.keys())
    out = [x.strip() for x in raw.split(",") if x.strip()]
    return [x for x in out if x in DOMAIN_CONFIGS]


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in records:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def print_stats(records: list[dict[str, Any]]) -> None:
    by_source: dict[str, int] = {}
    by_domain: dict[str, int] = {}

    for r in records:
        source = str(r.get("source") or "unknown")
        by_source[source] = by_source.get(source, 0) + 1

        src_url = str(r.get("source_url") or "")
        domain = urlparse(src_url).netloc or "unknown"
        by_domain[domain] = by_domain.get(domain, 0) + 1

    print("\n" + "=" * 60)
    print(f"총 추출: {len(records):,}개")
    print(f"소스 수: {len(by_source):,}개")
    print(f"도메인 수: {len(by_domain):,}개")

    print("\n[소스별]")
    for k, v in sorted(by_source.items(), key=lambda x: x[1], reverse=True):
        print(f"  {k:<24} {v:>6,}")

    print("\n[도메인별]")
    for k, v in sorted(by_domain.items(), key=lambda x: x[1], reverse=True):
        print(f"  {k:<30} {v:>6,}")
    print("=" * 60 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="다중 도메인 레시피 크롤링 + YouTube 구조화")
    parser.add_argument("--domains", type=str, default="all", help="대상 도메인 키 목록 (콤마 구분) 또는 all")
    parser.add_argument("--per-domain", type=int, default=500, help="도메인별 최대 추출 수")
    parser.add_argument("--delay", type=float, default=0.8, help="요청 간 딜레이(초)")
    parser.add_argument("--youtube", action="store_true", help="YouTube 채널 수집 활성화")
    parser.add_argument("--youtube-max-per-channel", type=int, default=50, help="채널당 최대 영상 수")
    parser.add_argument("--output", type=Path, default=Path("data/reference_recipes_multidomain.jsonl"), help="JSONL 출력 경로")
    args = parser.parse_args()

    selected = parse_domain_list(args.domains)
    if not selected and not args.youtube:
        parser.error("유효한 도메인이 없습니다. --domains 값을 확인하세요.")

    started = time.monotonic()
    all_records: list[dict[str, Any]] = []

    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=20.0) as client:
        for key in selected:
            config = DOMAIN_CONFIGS[key]
            records = crawl_domain(client, config, limit=args.per_domain, delay=args.delay)
            all_records.extend(records)

    if args.youtube:
        all_records.extend(crawl_youtube(args.youtube_max_per_channel, delay=args.delay))

    all_records = unique_by_source_url(all_records)
    write_jsonl(args.output, all_records)

    elapsed = time.monotonic() - started
    print_stats(all_records)
    print(f"출력 파일: {args.output.resolve()}")
    print(f"소요 시간: {elapsed/60:.1f}분")


if __name__ == "__main__":
    main()
