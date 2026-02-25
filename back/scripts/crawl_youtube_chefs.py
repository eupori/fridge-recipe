"""YouTube 셰프 채널 크롤러 — 자막 → Haiku 구조화"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

import httpx
from youtube_transcript_api import YouTubeTranscriptApi

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.crawl_utils import (
    extract_key_ingredients,
    get_session,
    polite_delay,
    save_recipe,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# 대상 셰프 채널
CHEF_CHANNELS = [
    {
        "name": "백종원",
        "channel_id": "UCyn-K7rZLXjGl7VXGweIlcA",
        "source_prefix": "youtube_백종원",
    },
    {
        "name": "류수영",
        "channel_id": "UCW_FCSKNI4kO57dBVLFMJYQ",
        "source_prefix": "youtube_류수영",
    },
]

MAX_VIDEOS_PER_CHANNEL = 50


def get_channel_videos(
    channel_id: str, api_key: str, max_results: int = 50
) -> list[dict]:
    """YouTube Data API로 채널의 인기 영상 조회"""
    videos: list[dict] = []
    url = "https://www.googleapis.com/youtube/v3/search"

    with httpx.Client(timeout=10.0) as client:
        params = {
            "key": api_key,
            "channelId": channel_id,
            "part": "snippet",
            "type": "video",
            "order": "viewCount",
            "maxResults": min(max_results, 50),
            "relevanceLanguage": "ko",
        }

        try:
            resp = client.get(url, params=params)
            resp.raise_for_status()

            for item in resp.json().get("items", []):
                video_id = item.get("id", {}).get("videoId")
                title = item.get("snippet", {}).get("title", "")
                if video_id and title:
                    videos.append({"video_id": video_id, "title": title})
        except Exception as e:
            logger.warning(f"채널 영상 조회 실패 ({channel_id}): {e}")

    return videos


def get_transcript(video_id: str) -> str | None:
    """YouTube 자막 추출 (한국어 우선, API 버전 호환)"""
    # New API (>=1.0)
    try:
        ytt = YouTubeTranscriptApi()
        fetched = ytt.fetch(video_id, languages=["ko"])
        return " ".join(snippet.text for snippet in fetched)
    except (AttributeError, TypeError):
        pass
    except Exception:
        pass

    # Old API (<1.0)
    try:
        entries = YouTubeTranscriptApi.get_transcript(
            video_id, languages=["ko"]
        )
        return " ".join(entry["text"] for entry in entries)
    except Exception as e:
        logger.debug(f"자막 추출 실패 ({video_id}): {e}")
        return None


def structure_with_haiku(transcript: str, video_title: str) -> dict | None:
    """Claude Haiku로 자막 → 구조화된 레시피 JSON"""
    prompt = (
        "다음은 요리 영상의 자막입니다. 레시피를 추출하여 JSON으로 반환하세요.\n\n"
        f"영상 제목: {video_title}\n\n"
        f"자막:\n{transcript[:3000]}\n\n"
        '다음 JSON 형식으로만 답하세요 (설명 없이 JSON만):\n'
        "{\n"
        '    "title": "레시피 제목 (한국어)",\n'
        '    "category": "밥/국물/반찬단품/면분식 중 하나",\n'
        '    "all_ingredients": ["재료1 분량", "재료2 분량"],\n'
        '    "steps": ["1단계", "2단계"],\n'
        '    "time_min": 조리시간(분, 숫자만),\n'
        '    "servings": 인분(숫자만)\n'
        "}\n\n"
        "레시피가 아닌 영상이면 null을 반환하세요."
    )

    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--model", "haiku"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            logger.debug(f"Haiku 호출 실패: {result.stderr[:200]}")
            return None

        output = result.stdout.strip()
        if output.lower() == "null" or not output:
            return None

        # 마크다운 코드블록 제거
        output = re.sub(r"^```(?:json)?\n?", "", output)
        output = re.sub(r"\n?```$", "", output)

        data = json.loads(output)

        if (
            not data.get("title")
            or not data.get("all_ingredients")
            or not data.get("steps")
        ):
            return None

        valid_categories = {"밥", "국물", "반찬단품", "면분식"}
        if data.get("category") not in valid_categories:
            data["category"] = "반찬단품"

        return data
    except (json.JSONDecodeError, subprocess.TimeoutExpired) as e:
        logger.debug(f"Haiku 결과 파싱 실패: {e}")
        return None
    except FileNotFoundError:
        logger.error(
            "claude CLI가 설치되지 않았습니다. YouTube 크롤러를 건너뜁니다."
        )
        return None


def crawl_youtube_chefs() -> int:
    """YouTube 셰프 채널 크롤링. 저장된 레시피 수 반환."""
    api_key = os.environ.get("YOUTUBE_API_KEY", "")
    if not api_key:
        logger.warning(
            "YOUTUBE_API_KEY가 설정되지 않았습니다. YouTube 크롤링 건너뜀."
        )
        return 0

    db = get_session()
    saved_count = 0

    for chef in CHEF_CHANNELS:
        logger.info(f"채널 크롤링 시작: {chef['name']}")

        videos = get_channel_videos(
            chef["channel_id"], api_key, MAX_VIDEOS_PER_CHANNEL
        )
        logger.info(f"  {len(videos)}개 영상 발견")

        for video in videos:
            video_url = (
                f"https://www.youtube.com/watch?v={video['video_id']}"
            )

            transcript = get_transcript(video["video_id"])
            if not transcript:
                logger.debug(f"  자막 없음: {video['title']}")
                continue

            polite_delay(0.5, 1.0)

            structured = structure_with_haiku(transcript, video["title"])
            if not structured:
                logger.debug(f"  구조화 실패: {video['title']}")
                continue

            key_ingredients = extract_key_ingredients(
                structured["all_ingredients"]
            )

            data = {
                "title": structured["title"],
                "category": structured["category"],
                "key_ingredients": key_ingredients,
                "all_ingredients": structured["all_ingredients"],
                "steps": structured["steps"],
                "technique": None,
                "time_min": structured.get("time_min"),
                "servings": structured.get("servings"),
                "source": chef["source_prefix"],
                "source_url": video_url,
                "view_count": 0,
                "rating": None,
            }

            if save_recipe(db, data):
                saved_count += 1
                logger.info(f"  저장: {structured['title']}")
                if saved_count % 20 == 0:
                    logger.info(f"  진행: {saved_count}개 저장됨")

    db.close()
    logger.info(f"YouTube 셰프 크롤링 완료: {saved_count}개 저장")
    return saved_count


if __name__ == "__main__":
    crawl_youtube_chefs()
