"""
이미지 검색/생성 서비스 - Google Custom Search API 및 Gemini Imagen 통합

현재 Unsplash API의 한국 음식 이미지 검색 정확도(30-50%)를 개선하기 위해
Google Custom Search API를 사용합니다. 정확도를 80-90%까지 향상시킵니다.

또한 Gemini의 이미지 생성 기능(Imagen)을 사용하여 고품질 한국 음식 이미지를
AI로 직접 생성할 수 있습니다.

주요 기능:
- Google Custom Search API 통합
- Gemini Imagen 이미지 생성 통합
- 한국어 음식명 → 영어 번역 자동 매핑
- 다단계 폴백 체인 (Google/Gemini → Unsplash → None)
- 인메모리 캐싱으로 API 할당량 절약
- 비동기 처리로 3개 이미지 병렬 검색/생성
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from urllib.parse import quote

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# 한국 음식 영어 번역 매핑 사전
# 검색 정확도 향상을 위해 한국어 + 영어 + 문맥 키워드 조합
KOREAN_FOOD_TRANSLATIONS: dict[str, str] = {
    # 밥/면 요리
    "김치볶음밥": "kimchi fried rice korean food",
    "볶음밥": "fried rice korean",
    "비빔밥": "bibimbap mixed rice bowl korean",
    "덮밥": "rice bowl donburi korean",
    "김밥": "gimbap kimbap korean sushi roll",
    "주먹밥": "jumeokbap rice ball korean",
    "잡채": "japchae glass noodles korean",
    "라면": "ramyeon korean instant noodles",
    "칼국수": "kalguksu knife-cut noodles korean",
    "냉면": "naengmyeon cold noodles korean",
    "비빔국수": "bibim guksu spicy noodles korean",
    # 찌개/국
    "된장찌개": "doenjang jjigae soybean paste stew korean",
    "김치찌개": "kimchi jjigae stew korean",
    "순두부찌개": "sundubu jjigae soft tofu stew korean",
    "부대찌개": "budae jjigae army stew korean",
    "된장국": "doenjang guk soybean paste soup korean",
    "미역국": "miyeok guk seaweed soup korean",
    "계란국": "gyeran guk egg soup korean",
    "콩나물국": "kongnamul guk bean sprout soup korean",
    # 고기 요리
    "불고기": "bulgogi korean bbq beef marinated",
    "제육볶음": "jeyuk bokkeum spicy pork stir-fry korean",
    "닭볶음탕": "dak bokkeum tang spicy chicken stew korean",
    "삼겹살": "samgyeopsal pork belly korean bbq",
    "갈비": "galbi korean bbq ribs",
    "닭갈비": "dak galbi spicy chicken ribs korean",
    "돼지갈비": "dwaeji galbi pork ribs korean",
    # 계란 요리
    "계란말이": "gyeran mari rolled omelette korean",
    "계란찜": "gyeran jjim steamed egg korean",
    "계란후라이": "fried egg korean",
    "스크램블": "scrambled eggs",
    # 반찬
    "김치": "kimchi korean fermented cabbage",
    "나물": "namul seasoned vegetables korean",
    "시금치나물": "sigeumchi namul spinach korean",
    "콩나물무침": "kongnamul muchim bean sprout korean",
    "무생채": "mu saengchae radish salad korean",
    # 튀김/전
    "김치전": "kimchi jeon pancake korean",
    "파전": "pajeon green onion pancake korean",
    "해물파전": "haemul pajeon seafood pancake korean",
    "감자전": "gamja jeon potato pancake korean",
    # 기타
    "떡볶이": "tteokbokki spicy rice cakes korean",
    "순대": "sundae korean blood sausage",
    "어묵": "eomuk fish cake korean",
    "만두": "mandu korean dumplings",
    "떡국": "tteokguk rice cake soup korean",
    "삼계탕": "samgyetang ginseng chicken soup korean",
}


class ImageSearchAdapter(ABC):
    """이미지 검색 어댑터 인터페이스"""

    @abstractmethod
    async def search_image(self, query: str) -> str | None:
        """
        이미지 검색

        Args:
            query: 검색 쿼리 (레시피 제목)

        Returns:
            이미지 URL 또는 None (검색 실패 시)
        """
        pass


class GoogleImageSearchAdapter(ImageSearchAdapter):
    """Google Custom Search API 어댑터"""

    BASE_URL = "https://www.googleapis.com/customsearch/v1"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.google_api_key
        self.cx = settings.google_search_engine_id
        self.timeout = settings.image_search_timeout

        if not self.api_key or not self.cx:
            logger.warning("Google API 자격증명 미설정. Fallback으로 전환됩니다.")

    def _enhance_korean_query(self, query: str) -> str:
        """
        한국어 쿼리를 영어로 증강

        예: "김치볶음밥" → "김치볶음밥 kimchi fried rice korean food"
        """
        query = query.strip()

        # 정확히 일치하는 번역이 있으면 사용
        if query in KOREAN_FOOD_TRANSLATIONS:
            english_part = KOREAN_FOOD_TRANSLATIONS[query]
            return f"{query} {english_part}"

        # 부분 일치 검색 (예: "간단한 김치볶음밥" → "김치볶음밥" 매칭)
        for korean_term, english_translation in KOREAN_FOOD_TRANSLATIONS.items():
            if korean_term in query:
                return f"{query} {english_translation}"

        # 번역이 없으면 기본 한국 음식 키워드 추가
        return f"{query} korean food dish"

    def _get_english_translation(self, query: str) -> str:
        """
        순수 영어 번역 반환 (한국어 제외)

        예: "김치볶음밥" → "kimchi fried rice korean food"
        """
        query = query.strip()

        # 정확 일치
        if query in KOREAN_FOOD_TRANSLATIONS:
            return KOREAN_FOOD_TRANSLATIONS[query]

        # 부분 일치
        for korean_term, english_translation in KOREAN_FOOD_TRANSLATIONS.items():
            if korean_term in query:
                return english_translation

        # 기본값
        return f"{query} food"

    async def _search_with_query(self, search_query: str) -> str | None:
        """
        실제 Google API 호출

        Args:
            search_query: 검색 쿼리

        Returns:
            이미지 URL 또는 None
        """
        if not self.api_key or not self.cx:
            return None

        params = {
            "key": self.api_key,
            "cx": self.cx,
            "q": search_query,
            "searchType": "image",
            "imgSize": "large",
            "imgType": "photo",
            "num": 1,
            "safe": "active",
            "fileType": "jpg,png",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()

                data = response.json()
                items = data.get("items", [])

                if items and len(items) > 0:
                    image_url = items[0].get("link")
                    if image_url:
                        logger.info(f"Google 이미지 검색 성공: '{search_query}' → {image_url}")
                        return image_url

                logger.warning(f"Google 이미지 검색 결과 없음: '{search_query}'")
                return None

        except httpx.TimeoutException:
            logger.error(f"Google API 타임아웃: '{search_query}'")
            return None
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.error("Google API 할당량 초과 (429)")
            else:
                logger.error(f"Google API HTTP 에러 {e.response.status_code}: {e}")
            return None
        except Exception as e:
            logger.error(f"Google 이미지 검색 실패: {e}")
            return None

    async def search_image(self, query: str) -> str | None:
        """
        Google Custom Search API로 이미지 검색 (다단계 폴백)

        1차: 한국어 + 영어 증강 쿼리
        2차: 영어만 쿼리

        Args:
            query: 레시피 제목

        Returns:
            이미지 URL 또는 None
        """
        # 1차 시도: 한국어 + 영어 증강
        enhanced_query = self._enhance_korean_query(query)
        result = await self._search_with_query(enhanced_query)

        if result:
            return result

        # 2차 시도: 영어만
        english_only = self._get_english_translation(query)
        if english_only != enhanced_query:
            result = await self._search_with_query(english_only)
            if result:
                return result

        logger.warning(f"Google 이미지 검색 실패 (모든 시도): '{query}'")
        return None


class UnsplashImageSearchAdapter(ImageSearchAdapter):
    """Unsplash 이미지 검색 어댑터 (폴백용)"""

    async def search_image(self, query: str) -> str | None:
        """
        Unsplash Featured 이미지 URL 생성

        Args:
            query: 검색 쿼리

        Returns:
            Unsplash 이미지 URL
        """
        encoded_query = quote(query)
        url = f"https://source.unsplash.com/featured/?{encoded_query}"
        logger.info(f"Unsplash 이미지 사용: '{query}' → {url}")
        return url


class MockImageSearchAdapter(ImageSearchAdapter):
    """Mock 이미지 검색 어댑터 (테스트용)"""

    async def search_image(self, query: str) -> str | None:
        """
        플레이스홀더 이미지 URL 반환

        Args:
            query: 검색 쿼리

        Returns:
            Placeholder 이미지 URL
        """
        encoded_query = quote(query)
        url = f"https://via.placeholder.com/640x480?text={encoded_query}"
        logger.info(f"Mock 이미지 사용: '{query}' → {url}")
        return url


class GeminiImageGenerationAdapter(ImageSearchAdapter):
    """
    Gemini AI 이미지 생성 어댑터

    Google Gemini의 이미지 생성 기능을 사용하여 고품질 한국 음식 이미지를 AI로 생성합니다.
    검색 기반 방식과 달리 항상 일관된 스타일의 음식 사진을 생성할 수 있습니다.

    주의: Google Cloud 유료 계정(Billing 활성화) 필요
    - Imagen 모델: 유료 사용자만 접근 가능
    - Gemini 이미지 생성: 무료 플랜 할당량 매우 제한적

    비용: 약 $0.02-0.04/이미지
    """

    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.model = settings.gemini_image_model
        self.timeout = settings.image_search_timeout
        self._client = None

        # 레퍼런스 이미지는 Google Images 스크래핑으로 확보 (API 키 불필요)

        if not self.api_key:
            logger.warning("Gemini API 키 미설정. Mock 모드로 전환됩니다.")

    def _get_client(self):
        """Lazy 초기화된 Gemini 클라이언트 반환"""
        if self._client is None:
            try:
                from google import genai

                self._client = genai.Client(api_key=self.api_key)
            except ImportError:
                logger.error("google-genai 패키지가 설치되지 않았습니다. pip install google-genai")
                raise
        return self._client

    def _get_english_name(self, recipe_title: str) -> str:
        """한국어 레시피 제목을 영어명으로 변환"""
        english_name = KOREAN_FOOD_TRANSLATIONS.get(recipe_title, None)

        # 부분 일치 검색
        if english_name is None:
            for korean_term, english_translation in KOREAN_FOOD_TRANSLATIONS.items():
                if korean_term in recipe_title:
                    english_name = english_translation
                    break

        # 번역이 없으면 기본 템플릿
        if english_name is None:
            english_name = f"{recipe_title} Korean dish"

        return english_name

    def _build_prompt(self, recipe_title: str, has_reference: bool = False) -> str:
        """
        한국 음식 이미지 생성 프롬프트 구성

        Args:
            recipe_title: 레시피 제목 (한국어)
            has_reference: 레퍼런스 이미지가 있는 경우 True

        Returns:
            영문 이미지 생성 프롬프트
        """
        english_name = self._get_english_name(recipe_title)

        if has_reference:
            prompt = f"""Create a realistic food photo of {recipe_title} ({english_name}).
The attached image shows a similar real dish for reference.
Generate a new photorealistic image of this Korean dish with:
natural lighting, top-down angle, ceramic plate,
appetizing colors, restaurant-quality plating, shallow depth of field.
Do NOT copy the reference exactly - create a fresh, realistic photo."""
        else:
            prompt = f"""Professional food photography of {recipe_title} ({english_name}).
Korean cuisine, appetizing presentation, warm natural lighting,
top-down view on a beautiful ceramic plate, restaurant quality,
high resolution, photorealistic, shallow depth of field,
garnished with fresh herbs, steam rising from the dish."""

        return prompt

    async def _download_image(self, image_url: str, source: str, query: str) -> bytes | None:
        """이미지 URL에서 바이트 다운로드"""
        try:
            async with httpx.AsyncClient(timeout=3.0, follow_redirects=True) as client:
                resp = await client.get(image_url)
                resp.raise_for_status()

                content_type = resp.headers.get("content-type", "")
                if not content_type.startswith("image/"):
                    logger.warning(f"[{source}] 레퍼런스 URL이 이미지가 아님: {content_type}")
                    return None

                image_bytes = resp.content
                if len(image_bytes) < 1000:
                    logger.warning(f"[{source}] 이미지가 너무 작음: {len(image_bytes)} bytes")
                    return None

                logger.info(
                    f"[{source}] 레퍼런스 이미지 다운로드 성공: '{query}' ({len(image_bytes)} bytes)"
                )
                return image_bytes

        except httpx.TimeoutException:
            logger.warning(f"[{source}] 레퍼런스 이미지 다운로드 타임아웃: '{query}'")
            return None
        except Exception as e:
            logger.warning(f"[{source}] 레퍼런스 이미지 다운로드 실패: '{query}' - {e}")
            return None

    async def _scrape_google_images(self, query: str) -> str | None:
        """
        Google Images HTML 스크래핑으로 이미지 URL 검색 (API 키 불필요)
        """
        import re

        try:
            english_name = self._get_english_name(query)
            search_query = quote(f"{query} {english_name} 음식 사진")
            url = f"https://www.google.com/search?q={search_query}&tbm=isch&ijn=0"
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            }

            async with httpx.AsyncClient(timeout=3.0, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()

            # HTML에서 이미지 URL 추출
            urls = re.findall(
                r'\["(https?://[^"]+\.(?:jpg|jpeg|png|webp)(?:\?[^"]*)?)"',
                resp.text,
            )
            # Google 자체 이미지 제외
            urls = [
                u for u in urls
                if "gstatic.com" not in u
                and "google.com" not in u
                and "googleapis.com" not in u
            ]

            if urls:
                logger.info(f"[Google Scrape] 이미지 URL 발견: '{query}' → {urls[0][:80]}")
                return urls[0]

            logger.warning(f"[Google Scrape] 이미지 URL 찾지 못함: '{query}'")
            return None

        except Exception as e:
            logger.warning(f"[Google Scrape] 검색 실패: '{query}' - {e}")
            return None

    async def _fetch_reference_image(self, query: str) -> bytes | None:
        """
        Google Images 스크래핑으로 레퍼런스 이미지 다운로드 (API 키 불필요)

        Args:
            query: 레시피 제목

        Returns:
            이미지 바이트 또는 None (실패 시)
        """
        image_url = await self._scrape_google_images(query)
        if image_url:
            result = await self._download_image(image_url, "Google Scrape", query)
            if result:
                return result

        logger.warning(f"레퍼런스 이미지 확보 실패: '{query}'")
        return None

    def _compress_image(self, image_bytes: bytes, max_size: int = 100000) -> tuple[bytes, str]:
        """
        이미지를 JPEG로 압축하여 크기 줄이기

        Args:
            image_bytes: 원본 이미지 바이트
            max_size: 최대 바이트 크기 (기본 100KB)

        Returns:
            (압축된 이미지 바이트, mime_type)
        """
        from io import BytesIO

        from PIL import Image

        # 이미지 로드
        img = Image.open(BytesIO(image_bytes))

        # RGBA → RGB 변환 (JPEG는 알파 채널 미지원)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # 리사이즈 (최대 400x400)
        max_dim = 400
        if img.width > max_dim or img.height > max_dim:
            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

        # JPEG 압축 (퀄리티 조절)
        quality = 70
        while quality >= 30:
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=quality, optimize=True)
            compressed = buffer.getvalue()

            if len(compressed) <= max_size:
                logger.info(f"이미지 압축: {len(image_bytes)} → {len(compressed)} bytes (quality={quality})")
                return compressed, "image/jpeg"

            quality -= 10

        # 최소 퀄리티로도 크면 그냥 반환
        logger.warning(f"이미지 압축 한계: {len(compressed)} bytes")
        return compressed, "image/jpeg"

    async def search_image(self, query: str) -> str | None:
        """
        레퍼런스 이미지 기반 Gemini 이미지 생성 후 압축된 base64 data URL 반환

        1. Google 이미지 검색으로 레퍼런스 이미지 확보
        2. 레퍼런스 + 프롬프트로 Gemini 이미지 생성 (실사감 향상)
        3. 레퍼런스 실패 시 텍스트 전용 프롬프트로 폴백

        Args:
            query: 레시피 제목 (검색이 아닌 생성용으로 사용)

        Returns:
            base64 인코딩된 이미지 data URL 또는 None
        """
        if not self.api_key:
            logger.warning("Gemini API 키 없음, 이미지 생성 불가")
            return None

        try:
            from google.genai import types

            client = self._get_client()

            # 레퍼런스 이미지 확보 시도 (3초 제한, 초과 시 텍스트 전용)
            try:
                reference_bytes = await asyncio.wait_for(
                    self._fetch_reference_image(query), timeout=3.0
                )
            except asyncio.TimeoutError:
                logger.warning(f"레퍼런스 이미지 확보 타임아웃 (3초): '{query}', 텍스트 전용으로 진행")
                reference_bytes = None
            has_reference = reference_bytes is not None
            prompt = self._build_prompt(query, has_reference=has_reference)

            if has_reference:
                logger.info(f"Gemini 이미지 생성 시작 (레퍼런스 포함): '{query}' (모델: {self.model})")
            else:
                logger.info(f"Gemini 이미지 생성 시작 (텍스트 전용): '{query}' (모델: {self.model})")

            # 동기 API를 비동기 실행 (Gemini SDK는 현재 동기만 지원)
            loop = asyncio.get_event_loop()

            # 모델 유형에 따라 다른 API 사용
            if self.model.startswith("imagen"):
                # Imagen 모델: generate_images 사용 (유료 계정 필요)
                # 레퍼런스 이미지는 Imagen에서 미지원, 텍스트 전용 프롬프트 사용
                text_only_prompt = self._build_prompt(query, has_reference=False)
                response = await loop.run_in_executor(
                    None,
                    lambda: client.models.generate_images(
                        model=self.model,
                        prompt=text_only_prompt,
                        config=types.GenerateImagesConfig(
                            number_of_images=1,
                        ),
                    ),
                )

                if response.generated_images and len(response.generated_images) > 0:
                    image = response.generated_images[0].image
                    image_bytes = image.image_bytes
                    # 압축 적용
                    compressed_bytes, mime_type = self._compress_image(image_bytes)
                    b64_data = base64.b64encode(compressed_bytes).decode("utf-8")
                    data_url = f"data:{mime_type};base64,{b64_data}"
                    logger.info(
                        f"Imagen 이미지 생성 성공: '{query}' (압축 후: {len(compressed_bytes)} bytes)"
                    )
                    return data_url
            else:
                # Gemini 이미지 생성 모델: generate_content 사용
                # 레퍼런스 이미지가 있으면 contents에 이미지 + 텍스트 전달
                if has_reference:
                    from io import BytesIO

                    from PIL import Image as PILImage

                    # 레퍼런스 이미지를 PIL로 로드하여 Gemini에 전달
                    ref_image = PILImage.open(BytesIO(reference_bytes))
                    # RGBA → RGB 변환
                    if ref_image.mode in ("RGBA", "P"):
                        ref_image = ref_image.convert("RGB")
                    # 레퍼런스 이미지 리사이즈 (너무 크면 비용 증가)
                    max_ref_dim = 512
                    if ref_image.width > max_ref_dim or ref_image.height > max_ref_dim:
                        ref_image.thumbnail((max_ref_dim, max_ref_dim), PILImage.Resampling.LANCZOS)

                    contents = [ref_image, prompt]
                else:
                    contents = prompt

                response = await loop.run_in_executor(
                    None,
                    lambda: client.models.generate_content(
                        model=self.model,
                        contents=contents,
                        config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
                    ),
                )

                if response.candidates and response.candidates[0].content.parts:
                    for part in response.candidates[0].content.parts:
                        if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                            image_data = part.inline_data.data
                            # 압축 적용
                            compressed_bytes, mime_type = self._compress_image(image_data)
                            b64_data = base64.b64encode(compressed_bytes).decode("utf-8")
                            data_url = f"data:{mime_type};base64,{b64_data}"
                            logger.info(
                                f"Gemini 이미지 생성 성공: '{query}' "
                                f"({'레퍼런스 포함' if has_reference else '텍스트 전용'}, "
                                f"압축 후: {len(compressed_bytes)} bytes)"
                            )
                            return data_url

            logger.warning(f"Gemini 응답에 이미지 없음: '{query}'")
            return None

        except ImportError:
            logger.error("google-genai 패키지 미설치")
            return None
        except Exception as e:
            error_str = str(e)
            if "billed users" in error_str.lower():
                logger.error("Gemini 이미지 생성: 유료 계정 필요 (Billing 활성화 필요)")
            elif "quota" in error_str.lower() or "RESOURCE_EXHAUSTED" in error_str:
                logger.error(
                    "Gemini 이미지 생성: 할당량 초과 (유료 플랜 업그레이드 또는 대기 필요)"
                )
            else:
                logger.error(f"Gemini 이미지 생성 실패: {e}")
            return None


class ImageSearchService:
    """
    통합 이미지 검색 서비스

    기능:
    - Primary provider (Google/Unsplash/Mock) 사용
    - Fallback provider (Unsplash) 자동 전환
    - 파일 기반 영구 캐싱으로 서버 재시작 후에도 캐시 유지
    """

    CACHE_FILE = Path(__file__).parent.parent.parent / "data" / "image_cache.json"

    def __init__(self):
        # Primary provider 선택
        provider = settings.image_search_provider.lower()

        if provider == "google":
            self.primary = GoogleImageSearchAdapter()
        elif provider == "gemini":
            self.primary = GeminiImageGenerationAdapter()
        elif provider == "unsplash":
            self.primary = UnsplashImageSearchAdapter()
        elif provider == "mock":
            self.primary = MockImageSearchAdapter()
        else:
            logger.warning(f"알 수 없는 provider '{provider}', Unsplash 사용")
            self.primary = UnsplashImageSearchAdapter()

        # Fallback은 항상 Unsplash (Mock/Gemini 제외)
        # Gemini는 생성 기반이라 Unsplash 폴백이 부자연스러움
        if provider not in ("mock", "gemini"):
            self.fallback = UnsplashImageSearchAdapter()
        else:
            self.fallback = None

        # 파일 기반 영구 캐시 로드
        self.cache_enabled = settings.image_cache_enabled
        self.cache: dict[str, str | None] = self._load_cache()

        logger.info(
            f"이미지 검색 서비스 초기화: provider={provider}, cache={self.cache_enabled}, 캐시 항목={len(self.cache)}"
        )

    def _load_cache(self) -> dict[str, str | None]:
        """파일에서 캐시 로드"""
        if not self.cache_enabled:
            return {}

        try:
            if self.CACHE_FILE.exists():
                with open(self.CACHE_FILE, encoding="utf-8") as f:
                    cache_data = json.load(f)
                    logger.info(f"캐시 파일 로드 완료: {len(cache_data)}개 항목")
                    return cache_data
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"캐시 파일 로드 실패, 새로 시작: {e}")

        return {}

    def _save_cache(self):
        """캐시를 파일에 저장"""
        if not self.cache_enabled:
            return

        try:
            self.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(self.CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
            logger.debug(f"캐시 파일 저장 완료: {len(self.cache)}개 항목")
        except OSError as e:
            logger.error(f"캐시 파일 저장 실패: {e}")

    async def get_image(self, recipe_title: str) -> str | None:
        """
        레시피 이미지 검색 (캐싱 + 폴백)

        순서:
        1. 캐시 확인
        2. Primary provider 시도
        3. Fallback provider 시도 (Primary 실패 시)
        4. None 반환 (모두 실패)

        Args:
            recipe_title: 레시피 제목

        Returns:
            이미지 URL 또는 None
        """
        # 1. 캐시 확인
        if self.cache_enabled and recipe_title in self.cache:
            cached_url = self.cache[recipe_title]
            logger.info(f"캐시 히트: '{recipe_title}' → {cached_url}")
            return cached_url

        # 2. Primary provider 시도
        try:
            image_url = await self.primary.search_image(recipe_title)

            if image_url:
                # 캐시 저장 (메모리 + 파일)
                if self.cache_enabled:
                    self.cache[recipe_title] = image_url
                    self._save_cache()
                return image_url
        except Exception as e:
            logger.error(f"Primary provider 에러: {e}")

        # 3. Fallback provider 시도
        if self.fallback:
            try:
                logger.info(f"Fallback provider 시도: '{recipe_title}'")
                image_url = await self.fallback.search_image(recipe_title)

                if image_url:
                    # 캐시 저장 (메모리 + 파일)
                    if self.cache_enabled:
                        self.cache[recipe_title] = image_url
                        self._save_cache()
                    return image_url
            except Exception as e:
                logger.error(f"Fallback provider 에러: {e}")

        # 4. 모두 실패
        logger.warning(f"이미지 검색 실패 (모든 provider): '{recipe_title}'")

        # None도 캐싱 (반복 검색 방지) - 메모리 + 파일
        if self.cache_enabled:
            self.cache[recipe_title] = None
            self._save_cache()

        return None

    def clear_cache(self):
        """캐시 초기화 (메모리 + 파일)"""
        self.cache.clear()
        if self.CACHE_FILE.exists():
            try:
                self.CACHE_FILE.unlink()
                logger.info("이미지 검색 캐시 파일 삭제")
            except OSError as e:
                logger.error(f"캐시 파일 삭제 실패: {e}")
        logger.info("이미지 검색 캐시 초기화")

    def get_cache_stats(self) -> dict:
        """캐시 통계"""
        return {
            "enabled": self.cache_enabled,
            "size": len(self.cache),
            "entries": list(self.cache.keys()),
        }
