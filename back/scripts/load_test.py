"""
프로덕션 부하 + 퀄리티 테스트
- 10개 다양한 재료 조합으로 동시 레시피 생성
- 응답 시간, 에러율, 레시피 퀄리티 측정
"""

import asyncio
import time
import json
import uuid
import statistics

import httpx

API_BASE = "https://recipe-api.eupori.dev/api/v1"
TEST_EMAIL = f"loadtest-{uuid.uuid4().hex[:8]}@test.com"
TEST_PASSWORD = "loadtest123!"

# 10개 다양한 테스트 시나리오
SCENARIOS = [
    {
        "name": "기본 볶음밥",
        "ingredients": ["밥", "김치", "계란"],
        "constraints": {"time_limit_min": 15, "servings": 1, "tools": [], "exclude": []},
    },
    {
        "name": "라면 요리",
        "ingredients": ["라면", "대파", "계란", "치즈"],
        "constraints": {"time_limit_min": 10, "servings": 1, "tools": [], "exclude": []},
    },
    {
        "name": "닭가슴살 볶음",
        "ingredients": ["닭가슴살", "양파", "간장", "마늘"],
        "constraints": {"time_limit_min": 20, "servings": 2, "tools": [], "exclude": []},
    },
    {
        "name": "된장찌개",
        "ingredients": ["두부", "된장", "대파", "감자", "호박"],
        "constraints": {"time_limit_min": 25, "servings": 2, "tools": [], "exclude": []},
    },
    {
        "name": "파스타",
        "ingredients": ["파스타면", "올리브오일", "마늘", "베이컨"],
        "constraints": {"time_limit_min": 20, "servings": 1, "tools": [], "exclude": []},
    },
    {
        "name": "토스트",
        "ingredients": ["식빵", "치즈", "햄", "버터"],
        "constraints": {"time_limit_min": 10, "servings": 1, "tools": [], "exclude": []},
    },
    {
        "name": "새우 요리",
        "ingredients": ["새우", "양파", "마늘", "버터", "소금"],
        "constraints": {"time_limit_min": 15, "servings": 2, "tools": [], "exclude": []},
    },
    {
        "name": "제육볶음",
        "ingredients": ["돼지고기", "고추장", "양파", "마늘", "대파"],
        "constraints": {"time_limit_min": 20, "servings": 2, "tools": [], "exclude": []},
    },
    {
        "name": "채소 볶음 (계란 제외)",
        "ingredients": ["브로콜리", "당근", "양파", "참기름", "간장"],
        "constraints": {"time_limit_min": 15, "servings": 1, "tools": [], "exclude": ["계란"]},
    },
    {
        "name": "소고기 감자조림",
        "ingredients": ["소고기", "감자", "당근", "양파", "간장", "마늘"],
        "constraints": {"time_limit_min": 30, "servings": 3, "tools": [], "exclude": []},
    },
]


async def signup_and_login(client: httpx.AsyncClient) -> str:
    """테스트 유저 생성 + 로그인 → JWT 반환"""
    # 회원가입
    resp = await client.post(f"{API_BASE}/auth/signup", json={
        "email": TEST_EMAIL, "password": TEST_PASSWORD,
    })
    if resp.status_code not in (200, 400):  # 400 = 이미 존재
        raise Exception(f"Signup failed: {resp.status_code} {resp.text}")

    # 로그인
    resp = await client.post(f"{API_BASE}/auth/login", json={
        "email": TEST_EMAIL, "password": TEST_PASSWORD,
    })
    if resp.status_code != 200:
        raise Exception(f"Login failed: {resp.status_code} {resp.text}")
    return resp.json()["access_token"]


async def poll_job(client: httpx.AsyncClient, job_id: str, timeout: int = 180) -> dict:
    """Job 완료 대기 (폴링)"""
    start = time.time()
    while time.time() - start < timeout:
        resp = await client.get(f"{API_BASE}/recommendations/jobs/{job_id}")
        if resp.status_code != 200:
            return {"status": "error", "error": f"Poll HTTP {resp.status_code}"}
        data = resp.json()
        if data["status"] == "completed":
            return data
        if data["status"] == "failed":
            return data
        await asyncio.sleep(3)
    return {"status": "timeout", "error": "Polling timeout"}


async def fetch_recommendation(client: httpx.AsyncClient, rec_id: str) -> dict | None:
    """추천 결과 조회"""
    resp = await client.get(f"{API_BASE}/recommendations/{rec_id}")
    if resp.status_code != 200:
        return None
    return resp.json()


def evaluate_quality(scenario: dict, result: dict) -> dict:
    """레시피 퀄리티 평가"""
    recipes = result.get("recipes", [])
    issues = []

    # 1. 레시피 개수
    if len(recipes) != 3:
        issues.append(f"레시피 {len(recipes)}개 (3개 필요)")

    for i, r in enumerate(recipes):
        prefix = f"레시피{i+1}({r.get('title', '?')})"

        # 2. 시간 제한
        time_limit = scenario["constraints"]["time_limit_min"]
        if r.get("time_min", 0) > time_limit:
            issues.append(f"{prefix}: {r['time_min']}분 > 제한 {time_limit}분")

        # 3. 조리 단계 수
        steps = r.get("steps", [])
        if len(steps) < 4:
            issues.append(f"{prefix}: 단계 {len(steps)}개 (최소 4개)")
        elif len(steps) > 8:
            issues.append(f"{prefix}: 단계 {len(steps)}개 (최대 8개)")

        # 4. 제외 재료 검사
        exclude = scenario["constraints"].get("exclude", [])
        for ex in exclude:
            title = r.get("title", "")
            all_ing = " ".join(r.get("ingredients_total", []))
            all_steps = " ".join(r.get("steps", []))
            if ex in title or ex in all_ing or ex in all_steps:
                issues.append(f"{prefix}: 제외 재료 '{ex}' 포함됨")

        # 5. 인분 확인
        if r.get("servings") != scenario["constraints"]["servings"]:
            issues.append(f"{prefix}: {r.get('servings')}인분 (요청: {scenario['constraints']['servings']})")

        # 6. 이미지 URL
        if not r.get("image_url"):
            issues.append(f"{prefix}: 이미지 없음")

        # 7. 재료 분류 확인
        have = r.get("ingredients_have", [])
        need = r.get("ingredients_need", [])
        total = r.get("ingredients_total", [])
        if not have:
            issues.append(f"{prefix}: 보유 재료 매칭 0개")

    # 8. 장보기 리스트
    shopping = result.get("shopping_list", [])
    if not shopping and any(r.get("ingredients_need") for r in recipes):
        issues.append("장보기 리스트 누락")

    return {
        "recipe_count": len(recipes),
        "titles": [r.get("title", "?") for r in recipes],
        "issues": issues,
        "quality_score": max(0, 100 - len(issues) * 15),
    }


async def run_scenario(
    client: httpx.AsyncClient, token: str, idx: int, scenario: dict
) -> dict:
    """시나리오 1개 실행"""
    headers = {"Authorization": f"Bearer {token}"}
    result = {
        "idx": idx,
        "name": scenario["name"],
        "ingredients": scenario["ingredients"],
        "status": "unknown",
        "time_sec": 0,
        "error": None,
        "quality": None,
    }

    start = time.time()
    try:
        # 1. 비동기 추천 요청
        resp = await client.post(
            f"{API_BASE}/recommendations/async",
            json=scenario,
            headers=headers,
            timeout=120,
        )
        if resp.status_code == 429:
            result["status"] = "rate_limited"
            result["error"] = "일일 제한 초과"
            result["time_sec"] = round(time.time() - start, 1)
            return result

        if resp.status_code != 200:
            result["status"] = "request_error"
            result["error"] = f"HTTP {resp.status_code}: {resp.text[:200]}"
            result["time_sec"] = round(time.time() - start, 1)
            return result

        data = resp.json()
        job_id = data.get("job_id")
        rec_id = data.get("recommendation_id")

        # 2. 캐시 히트 → 즉시 결과
        if rec_id and not job_id:
            rec = await fetch_recommendation(client, rec_id)
            result["time_sec"] = round(time.time() - start, 1)
            if rec:
                result["status"] = "cached"
                result["quality"] = evaluate_quality(scenario, rec)
            else:
                result["status"] = "fetch_error"
                result["error"] = "결과 조회 실패"
            return result

        # 3. Job 폴링
        job_result = await poll_job(client, job_id, timeout=180)
        if job_result.get("status") == "completed":
            rec_id = job_result["recommendation_id"]
            rec = await fetch_recommendation(client, rec_id)
            result["time_sec"] = round(time.time() - start, 1)
            if rec:
                result["status"] = "success"
                result["quality"] = evaluate_quality(scenario, rec)
            else:
                result["status"] = "fetch_error"
                result["error"] = "결과 조회 실패"
        elif job_result.get("status") == "failed":
            result["status"] = "failed"
            result["error"] = job_result.get("error", "알 수 없는 에러")
            result["time_sec"] = round(time.time() - start, 1)
        elif job_result.get("status") == "error":
            result["status"] = "poll_error"
            result["error"] = job_result.get("error", "폴링 오류")
            result["time_sec"] = round(time.time() - start, 1)
        else:
            result["status"] = "timeout"
            result["error"] = "3분 타임아웃"
            result["time_sec"] = round(time.time() - start, 1)

    except Exception as e:
        result["status"] = "exception"
        result["error"] = f"{type(e).__name__}: {e}"
        result["time_sec"] = round(time.time() - start, 1)

    return result


async def main():
    print("=" * 70)
    print("  프로덕션 부하 + 퀄리티 테스트 (10개 동시 요청)")
    print("=" * 70)

    async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=10)) as client:
        # 1. 테스트 유저 준비
        print(f"\n[준비] 테스트 유저: {TEST_EMAIL}")
        token = await signup_and_login(client)
        print("[준비] JWT 토큰 획득 완료\n")

        # 2. 5개씩 배치로 실행 (t3.medium 4GB)
        BATCH_SIZE = 5
        print(f"[테스트] 10개 시나리오 — {BATCH_SIZE}개씩 배치 실행...")
        total_start = time.time()
        results = []

        for batch_start in range(0, len(SCENARIOS), BATCH_SIZE):
            batch = SCENARIOS[batch_start:batch_start + BATCH_SIZE]
            batch_num = batch_start // BATCH_SIZE + 1
            print(f"  배치 {batch_num}: {', '.join(s['name'] for s in batch)}")
            tasks = [
                run_scenario(client, token, batch_start + i, s)
                for i, s in enumerate(batch)
            ]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            # 배치 간 서버 회복 대기
            if batch_start + BATCH_SIZE < len(SCENARIOS):
                await asyncio.sleep(5)

        total_time = round(time.time() - total_start, 1)

        # 3. 결과 출력
        print("\n" + "=" * 70)
        print("  결과 요약")
        print("=" * 70)

        success_count = 0
        cached_count = 0
        fail_count = 0
        times = []
        quality_scores = []

        for r in results:
            status_icon = {
                "success": "OK",
                "cached": "CACHE",
                "failed": "FAIL",
                "timeout": "TIMEOUT",
                "rate_limited": "LIMIT",
                "poll_error": "POLL",
                "request_error": "ERR",
                "fetch_error": "ERR",
                "exception": "ERR",
            }.get(r["status"], "?")

            quality_str = ""
            if r["quality"]:
                q = r["quality"]
                quality_str = f" | Q:{q['quality_score']}점 | {', '.join(q['titles'])}"
                if q["issues"]:
                    quality_str += f" | 이슈: {'; '.join(q['issues'])}"
                quality_scores.append(q["quality_score"])

            error_str = f" | {r['error']}" if r["error"] else ""

            print(
                f"  [{status_icon:>5}] #{r['idx']+1:2d} {r['name']:<16s} "
                f"{r['time_sec']:>6.1f}s{error_str}{quality_str}"
            )

            if r["status"] in ("success", "cached"):
                success_count += 1
                times.append(r["time_sec"])
            if r["status"] == "cached":
                cached_count += 1
            if r["status"] in ("failed", "timeout", "poll_error", "request_error", "fetch_error", "exception"):
                fail_count += 1

        # 4. 통계
        print("\n" + "-" * 70)
        print(f"  총 소요시간: {total_time}s")
        print(f"  성공: {success_count}/10 (캐시: {cached_count})")
        print(f"  실패: {fail_count}/10")
        print(f"  에러율: {fail_count/10*100:.0f}%")

        if times:
            print(f"  응답시간 - 평균: {statistics.mean(times):.1f}s | "
                  f"중앙값: {statistics.median(times):.1f}s | "
                  f"최소: {min(times):.1f}s | 최대: {max(times):.1f}s")

        if quality_scores:
            print(f"  퀄리티 - 평균: {statistics.mean(quality_scores):.0f}점 | "
                  f"최소: {min(quality_scores)}점 | 최대: {max(quality_scores)}점")

        rate_limited = sum(1 for r in results if r["status"] == "rate_limited")
        if rate_limited:
            print(f"  레이트 리밋: {rate_limited}건")

        print("-" * 70)


if __name__ == "__main__":
    asyncio.run(main())
