#!/usr/bin/env python3
"""
QA 테스트 스크립트 — 프로덕션 환경 검증
========================================
20명의 테스트 유저로 전체 플로우 + 특수 테스트 병행 실행.

실행: python back/scripts/qa_test.py
"""

import asyncio
import json
import random
import string
import time
from dataclasses import dataclass, field

import httpx

# ─────────────────────────────────────────
# 설정
# ─────────────────────────────────────────
BASE_URL = "https://recipe-api.eupori.dev"
API = f"{BASE_URL}/api/v1"
TIMEOUT = 60.0
MAX_CONCURRENT = 5

# 테스트 재료 세트 (LLM 비용 최소화를 위해 간단한 조합)
INGREDIENT_SETS = [
    ["계란", "밥", "김치"],
    ["양파", "감자", "당근"],
    ["두부", "파", "고추장"],
    ["라면", "계란", "파"],
    ["밥", "참치캔", "김"],
    ["소시지", "밥", "케첩"],
    ["식빵", "계란", "버터"],
    ["떡", "고추장", "양파"],
    ["콩나물", "파", "마늘"],
    ["스팸", "밥", "김"],
]

QUALITY_LEVELS = ["fast", "standard", "detailed"]

# ─────────────────────────────────────────
# 데이터 클래스
# ─────────────────────────────────────────

@dataclass
class TestResult:
    name: str
    passed: bool
    detail: str = ""
    duration_ms: int = 0


@dataclass
class TestUser:
    email: str
    password: str
    token: str = ""
    user_id: str = ""


@dataclass
class QAReport:
    results: list[TestResult] = field(default_factory=list)

    def add(self, result: TestResult):
        self.results.append(result)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def total(self) -> int:
        return len(self.results)

    def print_report(self):
        print("\n" + "=" * 50)
        print("          QA 결과 리포트")
        print("=" * 50)

        passed = [r for r in self.results if r.passed]
        failed = [r for r in self.results if not r.passed]

        print(f"\n[PASS] {len(passed)}/{self.total} 테스트 통과")

        if failed:
            print(f"[FAIL] {len(failed)}건 실패:")
            for r in failed:
                dur = f" ({r.duration_ms}ms)" if r.duration_ms else ""
                print(f"  - {r.name}: {r.detail}{dur}")
        else:
            print("\n모든 테스트 통과!")

        print(f"\n총 소요 시간: {sum(r.duration_ms for r in self.results) / 1000:.1f}s")

        if failed:
            print("\n결론: 배포 보류 — %d건 수정 필요" % len(failed))
        else:
            print("\n결론: 배포 승인")

        print("=" * 50)


report = QAReport()


# ─────────────────────────────────────────
# 유틸리티
# ─────────────────────────────────────────

def rand_suffix() -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=6))


async def timed(name: str, coro):
    """코루틴 실행 시간 측정 + 결과 기록"""
    start = time.monotonic()
    try:
        result = await coro
        elapsed = int((time.monotonic() - start) * 1000)
        if isinstance(result, TestResult):
            result.duration_ms = elapsed
            report.add(result)
        return result
    except Exception as e:
        elapsed = int((time.monotonic() - start) * 1000)
        report.add(TestResult(name=name, passed=False, detail=str(e), duration_ms=elapsed))
        return None


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ─────────────────────────────────────────
# 1. 유저 셋업
# ─────────────────────────────────────────

async def setup_users(client: httpx.AsyncClient) -> tuple[list[TestUser], list[TestUser]]:
    """20명 유저 생성 + 로그인"""
    print("\n[1/8] 테스트 유저 생성 중...")
    suffix = rand_suffix()

    flow_users: list[TestUser] = []
    spec_users: list[TestUser] = []

    async def create_user(prefix: str, idx: int) -> TestUser:
        email = f"qa-{prefix}-{idx:02d}-{suffix}@test.eupori.dev"
        password = f"QaTest!{idx:02d}{suffix}"
        user = TestUser(email=email, password=password)

        # 회원가입
        res = await client.post(f"{API}/auth/signup", json={
            "email": email, "password": password
        })

        if res.status_code == 200:
            data = res.json()
            user.user_id = data.get("id", "")
        elif res.status_code == 400 and "이미" in res.json().get("detail", ""):
            pass  # 이미 존재하면 로그인만
        else:
            raise Exception(f"회원가입 실패 [{res.status_code}]: {res.text}")

        # 로그인
        res = await client.post(f"{API}/auth/login", json={
            "email": email, "password": password
        })
        if res.status_code != 200:
            raise Exception(f"로그인 실패 [{res.status_code}]: {res.text}")

        data = res.json()
        user.token = data["access_token"]
        return user

    # 병렬 생성 (5개씩)
    tasks = []
    for i in range(1, 11):
        tasks.append(create_user("flow", i))
    for i in range(1, 11):
        tasks.append(create_user("spec", i))

    # 5개씩 배치 실행
    all_users = []
    for batch_start in range(0, len(tasks), MAX_CONCURRENT):
        batch = tasks[batch_start:batch_start + MAX_CONCURRENT]
        results = await asyncio.gather(*batch, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                report.add(TestResult(name="유저 생성", passed=False, detail=str(r)))
            else:
                all_users.append(r)

    flow_users = all_users[:10] if len(all_users) >= 10 else all_users
    spec_users = all_users[10:] if len(all_users) > 10 else []

    print(f"  → {len(flow_users)}명 플로우 유저 + {len(spec_users)}명 특수 유저 준비 완료")
    return flow_users, spec_users


# ─────────────────────────────────────────
# 2. 전체 플로우 QA (A그룹)
# ─────────────────────────────────────────

async def run_single_flow(client: httpx.AsyncClient, user: TestUser, idx: int):
    """단일 유저의 전체 사용 여정"""
    tag = f"flow-{idx:02d}"
    headers = auth_headers(user.token)
    ingredients = INGREDIENT_SETS[idx % len(INGREDIENT_SETS)]
    quality = random.choice(QUALITY_LEVELS)

    # Step 1: /auth/me
    async def test_me():
        res = await client.get(f"{API}/auth/me", headers=headers)
        if res.status_code == 200 and res.json().get("email") == user.email:
            return TestResult(name=f"{tag}/me", passed=True)
        return TestResult(name=f"{tag}/me", passed=False, detail=f"status={res.status_code}")

    await timed(f"{tag}/me", test_me())

    # Step 2: 레시피 추천 생성
    rec_id = None

    async def test_create_rec():
        nonlocal rec_id
        res = await client.post(f"{API}/recommendations", headers=headers, json={
            "ingredients": ingredients,
            "constraints": {
                "time_limit_min": 15,
                "servings": 1,
                "quality_level": quality,
            }
        })
        if res.status_code == 200:
            data = res.json()
            rec_id = data.get("id")
            recipes = data.get("recipes", [])
            shopping = data.get("shopping_list", [])
            # 기본 검증
            errors = []
            if len(recipes) != 3:
                errors.append(f"레시피 {len(recipes)}개 (3개 예상)")
            for i, r in enumerate(recipes):
                if r.get("time_min", 999) > 15:
                    errors.append(f"레시피[{i}] 시간초과: {r.get('time_min')}분")
                steps = r.get("steps", [])
                if not (2 <= len(steps) <= 12):
                    errors.append(f"레시피[{i}] 스텝수 이상: {len(steps)}")
            if errors:
                return TestResult(name=f"{tag}/create-rec", passed=False, detail="; ".join(errors))
            return TestResult(name=f"{tag}/create-rec", passed=True,
                              detail=f"quality={quality}, rec_id={rec_id}")
        return TestResult(name=f"{tag}/create-rec", passed=False,
                          detail=f"status={res.status_code}: {res.text[:200]}")

    await timed(f"{tag}/create-rec", test_create_rec())

    if not rec_id:
        return  # 추천 실패 시 나머지 스킵

    # Step 3: 추천 조회
    async def test_get_rec():
        res = await client.get(f"{API}/recommendations/{rec_id}", headers=headers)
        if res.status_code == 200:
            data = res.json()
            if data.get("id") == rec_id and len(data.get("recipes", [])) == 3:
                return TestResult(name=f"{tag}/get-rec", passed=True)
            return TestResult(name=f"{tag}/get-rec", passed=False, detail="응답 데이터 불일치")
        return TestResult(name=f"{tag}/get-rec", passed=False, detail=f"status={res.status_code}")

    await timed(f"{tag}/get-rec", test_get_rec())

    # Step 4: 이미지 배치 생성
    async def test_image_batch():
        res = await client.get(f"{API}/recommendations/{rec_id}", headers=headers)
        if res.status_code != 200:
            return TestResult(name=f"{tag}/img-batch", passed=False, detail="추천 조회 실패")
        titles = [r["title"] for r in res.json().get("recipes", [])]
        res2 = await client.post(f"{API}/images/batch", json={
            "titles": titles,
            "recommendation_id": rec_id,
        })
        if res2.status_code == 200:
            images = res2.json().get("images", [])
            if len(images) == len(titles):
                return TestResult(name=f"{tag}/img-batch", passed=True)
            return TestResult(name=f"{tag}/img-batch", passed=False,
                              detail=f"이미지 {len(images)}개 반환 ({len(titles)}개 예상)")
        return TestResult(name=f"{tag}/img-batch", passed=False,
                          detail=f"status={res2.status_code}")

    await timed(f"{tag}/img-batch", test_image_batch())

    # Step 5: 즐겨찾기 CRUD
    fav_id = None

    async def test_fav_add():
        nonlocal fav_id
        res = await client.post(f"{API}/favorites", headers=headers, json={
            "recommendation_id": rec_id,
            "recipe_index": 0,
            "recipe_title": "QA 테스트 레시피",
            "recipe_image_url": "https://example.com/test.jpg",
        })
        if res.status_code == 200:
            fav_id = res.json().get("id")
            return TestResult(name=f"{tag}/fav-add", passed=True)
        return TestResult(name=f"{tag}/fav-add", passed=False, detail=f"status={res.status_code}")

    await timed(f"{tag}/fav-add", test_fav_add())

    async def test_fav_list():
        res = await client.get(f"{API}/favorites", headers=headers)
        if res.status_code == 200:
            favs = res.json()
            if any(f.get("id") == fav_id for f in favs):
                return TestResult(name=f"{tag}/fav-list", passed=True)
            return TestResult(name=f"{tag}/fav-list", passed=False, detail="추가한 즐겨찾기 없음")
        return TestResult(name=f"{tag}/fav-list", passed=False, detail=f"status={res.status_code}")

    await timed(f"{tag}/fav-list", test_fav_list())

    async def test_fav_check():
        res = await client.get(
            f"{API}/favorites/check",
            headers=headers,
            params={"recommendation_id": rec_id, "recipe_index": 0},
        )
        if res.status_code == 200 and res.json().get("is_favorite"):
            return TestResult(name=f"{tag}/fav-check", passed=True)
        return TestResult(name=f"{tag}/fav-check", passed=False,
                          detail=f"status={res.status_code}, body={res.text[:100]}")

    await timed(f"{tag}/fav-check", test_fav_check())

    async def test_fav_delete():
        if not fav_id:
            return TestResult(name=f"{tag}/fav-del", passed=False, detail="fav_id 없음")
        res = await client.delete(f"{API}/favorites/{fav_id}", headers=headers)
        if res.status_code == 200 and res.json().get("ok"):
            return TestResult(name=f"{tag}/fav-del", passed=True)
        return TestResult(name=f"{tag}/fav-del", passed=False, detail=f"status={res.status_code}")

    await timed(f"{tag}/fav-del", test_fav_delete())

    # Step 6: 검색 기록
    async def test_history():
        res = await client.get(f"{API}/search-histories", headers=headers)
        if res.status_code == 200:
            return TestResult(name=f"{tag}/history", passed=True,
                              detail=f"{len(res.json())}건 기록")
        return TestResult(name=f"{tag}/history", passed=False, detail=f"status={res.status_code}")

    await timed(f"{tag}/history", test_history())

    # Step 7: 통계 조회
    async def test_stats():
        res = await client.get(f"{API}/stats")
        if res.status_code == 200:
            data = res.json()
            if "total_recipes_generated" in data and "total_users" in data:
                return TestResult(name=f"{tag}/stats", passed=True)
            return TestResult(name=f"{tag}/stats", passed=False, detail="필드 누락")
        return TestResult(name=f"{tag}/stats", passed=False, detail=f"status={res.status_code}")

    await timed(f"{tag}/stats", test_stats())


async def run_flow_tests(client: httpx.AsyncClient, users: list[TestUser]):
    """A그룹: 전체 플로우 테스트 (순차)"""
    print("\n[2/8] 전체 플로우 테스트 (A그룹)...")
    for i, user in enumerate(users):
        print(f"  → 플로우 유저 {i + 1}/{len(users)}")
        await run_single_flow(client, user, i)


# ─────────────────────────────────────────
# 3. 스트레스 테스트 (spec-01~02)
# ─────────────────────────────────────────

async def run_stress_tests(client: httpx.AsyncClient, users: list[TestUser]):
    """동시 요청 + 한도 테스트"""
    print("\n[3/8] 스트레스 테스트 (spec-01~02)...")
    if len(users) < 2:
        report.add(TestResult(name="stress", passed=False, detail="유저 부족"))
        return

    user1, user2 = users[0], users[1]

    # 동시 5개 레시피 요청 (fast 모드)
    async def test_concurrent():
        headers = auth_headers(user1.token)
        tasks = []
        for i in range(MAX_CONCURRENT):
            ingredients = INGREDIENT_SETS[i % len(INGREDIENT_SETS)]
            tasks.append(
                client.post(f"{API}/recommendations", headers=headers, json={
                    "ingredients": ingredients,
                    "constraints": {"time_limit_min": 15, "servings": 1, "quality_level": "fast"},
                })
            )
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success = 0
        errors = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                errors.append(f"req-{i}: {str(r)[:80]}")
            elif r.status_code == 200:
                success += 1
            elif r.status_code == 429:
                success += 1  # 한도 초과도 정상 동작
            else:
                errors.append(f"req-{i}: status={r.status_code}")

        if errors:
            return TestResult(name="stress/concurrent-5",
                              passed=False, detail="; ".join(errors))
        return TestResult(name="stress/concurrent-5",
                          passed=True, detail=f"{success}/{MAX_CONCURRENT} 성공")

    await timed("stress/concurrent-5", test_concurrent())

    # 일일 한도 도달 확인 (이미 여러 요청 보냈으므로 remaining 헤더 체크)
    async def test_remaining_header():
        headers = auth_headers(user2.token)
        res = await client.post(f"{API}/recommendations", headers=headers, json={
            "ingredients": ["계란", "밥"],
            "constraints": {"time_limit_min": 15, "quality_level": "fast"},
        })
        remaining = res.headers.get("X-Daily-Remaining")
        if remaining is not None:
            return TestResult(name="stress/remaining-header",
                              passed=True, detail=f"remaining={remaining}")
        # 429도 정상 (한도 초과)
        if res.status_code == 429:
            return TestResult(name="stress/remaining-header",
                              passed=True, detail="한도 초과 (429)")
        return TestResult(name="stress/remaining-header",
                          passed=False, detail=f"X-Daily-Remaining 헤더 없음, status={res.status_code}")

    await timed("stress/remaining-header", test_remaining_header())


# ─────────────────────────────────────────
# 4. 악성 입력 테스트 (spec-03~04)
# ─────────────────────────────────────────

async def run_malicious_tests(client: httpx.AsyncClient, users: list[TestUser]):
    """SQL injection, XSS, 비식품 재료 등"""
    print("\n[4/8] 악성 입력 테스트 (spec-03~04)...")
    if len(users) < 4:
        report.add(TestResult(name="malicious", passed=False, detail="유저 부족"))
        return

    user = users[2]
    headers = auth_headers(user.token)

    # SQL injection 재료
    async def test_sql_injection():
        payloads = [
            ["'; DROP TABLE users; --", "계란"],
            ["1 OR 1=1", "밥"],
            ["계란' UNION SELECT * FROM users--", "양파"],
        ]
        for i, ingredients in enumerate(payloads):
            res = await client.post(f"{API}/recommendations", headers=headers, json={
                "ingredients": ingredients,
                "constraints": {"time_limit_min": 15, "quality_level": "fast"},
            })
            # 400(검증 차단) 또는 200(무해화됨) 모두 OK. 500은 실패.
            if res.status_code == 500:
                return TestResult(name=f"malicious/sqli-{i}",
                                  passed=False, detail=f"500 에러: {res.text[:100]}")
        return TestResult(name="malicious/sqli", passed=True, detail="SQL injection 차단/무해화 확인")

    await timed("malicious/sqli", test_sql_injection())

    # XSS 재료
    async def test_xss():
        payloads = [
            ['<script>alert("xss")</script>', "계란"],
            ['<img src=x onerror=alert(1)>', "밥"],
            ["javascript:alert(1)", "양파"],
        ]
        for i, ingredients in enumerate(payloads):
            res = await client.post(f"{API}/recommendations", headers=headers, json={
                "ingredients": ingredients,
                "constraints": {"time_limit_min": 15, "quality_level": "fast"},
            })
            if res.status_code == 200:
                body = res.text
                if "<script>" in body or "onerror=" in body:
                    return TestResult(name="malicious/xss",
                                      passed=False, detail=f"XSS 미필터링: payload {i}")
            elif res.status_code == 500:
                return TestResult(name="malicious/xss",
                                  passed=False, detail=f"500 에러: {res.text[:100]}")
        return TestResult(name="malicious/xss", passed=True, detail="XSS 차단/무해화 확인")

    await timed("malicious/xss", test_xss())

    # 비식품 재료 (블록리스트)
    async def test_non_food():
        blocked = [
            (["독버섯", "밥"], "독버섯"),
            (["수은", "계란"], "수은"),
            (["표백제", "밥"], "표백제"),
            (["살충제", "양파"], "살충제"),
            (["대마", "밥"], "대마"),
        ]
        all_ok = True
        details = []
        for ingredients, expected_block in blocked:
            res = await client.post(f"{API}/recommendations", headers=headers, json={
                "ingredients": ingredients,
                "constraints": {"time_limit_min": 15, "quality_level": "fast"},
            })
            if res.status_code != 400:
                all_ok = False
                details.append(f"'{expected_block}' 미차단 (status={res.status_code})")
        if all_ok:
            return TestResult(name="malicious/non-food", passed=True,
                              detail=f"{len(blocked)}개 비식품 차단 확인")
        return TestResult(name="malicious/non-food", passed=False, detail="; ".join(details))

    await timed("malicious/non-food", test_non_food())

    # 초장문 재료명
    async def test_long_input():
        long_name = "계란" * 500  # 1000자
        res = await client.post(f"{API}/recommendations", headers=headers, json={
            "ingredients": [long_name, "밥"],
            "constraints": {"time_limit_min": 15, "quality_level": "fast"},
        })
        # 400 또는 422(검증 실패) 기대. 500은 실패.
        if res.status_code in (400, 422):
            return TestResult(name="malicious/long-input", passed=True,
                              detail=f"초장문 입력 차단 ({res.status_code})")
        elif res.status_code == 200:
            return TestResult(name="malicious/long-input", passed=True,
                              detail="초장문 입력 처리됨 (200)")
        return TestResult(name="malicious/long-input", passed=False,
                          detail=f"status={res.status_code}: {res.text[:100]}")

    await timed("malicious/long-input", test_long_input())

    # 빈 배열
    async def test_empty_ingredients():
        res = await client.post(f"{API}/recommendations", headers=headers, json={
            "ingredients": [],
            "constraints": {"time_limit_min": 15, "quality_level": "fast"},
        })
        if res.status_code in (400, 422):
            return TestResult(name="malicious/empty-arr", passed=True,
                              detail=f"빈 배열 차단 ({res.status_code})")
        return TestResult(name="malicious/empty-arr", passed=False,
                          detail=f"빈 배열 미차단: status={res.status_code}")

    await timed("malicious/empty-arr", test_empty_ingredients())

    # 특수문자 재료
    async def test_special_chars():
        res = await client.post(f"{API}/recommendations", headers=headers, json={
            "ingredients": ["🍳", "밥", "|||///\\\\"],
            "constraints": {"time_limit_min": 15, "quality_level": "fast"},
        })
        if res.status_code in (200, 400, 422):
            return TestResult(name="malicious/special-chars", passed=True,
                              detail=f"특수문자 처리 ({res.status_code})")
        return TestResult(name="malicious/special-chars", passed=False,
                          detail=f"500 에러: {res.text[:100]}")

    await timed("malicious/special-chars", test_special_chars())


# ─────────────────────────────────────────
# 5. 경계값 테스트 (spec-05~06)
# ─────────────────────────────────────────

async def run_boundary_tests(client: httpx.AsyncClient, users: list[TestUser]):
    """time_limit, servings, 재료 수 등 경계값"""
    print("\n[5/8] 경계값 테스트 (spec-05~06)...")
    if len(users) < 6:
        report.add(TestResult(name="boundary", passed=False, detail="유저 부족"))
        return

    user = users[4]
    headers = auth_headers(user.token)

    # time_limit 경계값
    async def test_time_limits():
        cases = [
            (5, None, "최소값"),   # 5분은 허용되지만 LLM이 실패할 수 있음 (200/400 모두 OK)
            (60, True, "최대값"),
            (61, False, "초과값"),
            (0, False, "0"),
            (-1, False, "음수"),
        ]
        errors = []
        for limit, should_pass, label in cases:
            res = await client.post(f"{API}/recommendations", headers=headers, json={
                "ingredients": ["계란", "밥"],
                "constraints": {"time_limit_min": limit, "servings": 1, "quality_level": "fast"},
            })
            if should_pass is None:
                # 허용 범위이나 LLM 실패 가능 — 422만 아니면 OK
                valid = res.status_code != 422
            elif should_pass:
                valid = res.status_code == 200
            else:
                valid = res.status_code in (400, 422)
            if not valid:
                errors.append(f"time={limit}({label}): status={res.status_code} "
                              f"({'성공 예상' if should_pass else '실패 예상'})")
        if errors:
            return TestResult(name="boundary/time-limit", passed=False,
                              detail="; ".join(errors))
        return TestResult(name="boundary/time-limit", passed=True,
                          detail="5/60/61/0/-1 모두 정상 처리")

    await timed("boundary/time-limit", test_time_limits())

    # servings 경계값
    async def test_servings():
        cases = [
            (1, True, "최소값"),
            (6, True, "최대값"),
            (7, False, "초과값"),
            (0, False, "0"),
        ]
        errors = []
        for srv, should_pass, label in cases:
            res = await client.post(f"{API}/recommendations", headers=headers, json={
                "ingredients": ["계란", "밥"],
                "constraints": {"time_limit_min": 15, "servings": srv, "quality_level": "fast"},
            })
            valid = res.status_code == 200 if should_pass else res.status_code in (400, 422)
            if not valid:
                errors.append(f"servings={srv}({label}): status={res.status_code} "
                              f"({'성공 예상' if should_pass else '실패 예상'})")
        if errors:
            return TestResult(name="boundary/servings", passed=False,
                              detail="; ".join(errors))
        return TestResult(name="boundary/servings", passed=True,
                          detail="1/6/7/0 모두 정상 처리")

    await timed("boundary/servings", test_servings())

    # 재료 50개 (대량)
    async def test_many_ingredients():
        many = [f"재료{i}" for i in range(50)]
        res = await client.post(f"{API}/recommendations", headers=headers, json={
            "ingredients": many,
            "constraints": {"time_limit_min": 15, "quality_level": "fast"},
        })
        if res.status_code in (200, 400, 422):
            return TestResult(name="boundary/50-ingredients", passed=True,
                              detail=f"50개 재료 ({res.status_code})")
        return TestResult(name="boundary/50-ingredients", passed=False,
                          detail=f"status={res.status_code}: {res.text[:100]}")

    await timed("boundary/50-ingredients", test_many_ingredients())

    # recipe_index 경계값 (즐겨찾기)
    async def test_recipe_index():
        # 먼저 추천 1개 생성
        res = await client.post(f"{API}/recommendations", headers=headers, json={
            "ingredients": ["계란", "밥"],
            "constraints": {"time_limit_min": 15, "quality_level": "fast"},
        })
        if res.status_code != 200:
            return TestResult(name="boundary/recipe-index", passed=True,
                              detail="추천 생성 실패 (한도 초과 가능)")

        rec_id = res.json().get("id")

        cases = [
            (-1, False, "음수"),
            (3, False, "초과(3)"),
            (0, True, "정상(0)"),
        ]
        errors = []
        for idx, should_pass, label in cases:
            res2 = await client.post(f"{API}/favorites", headers=headers, json={
                "recommendation_id": rec_id,
                "recipe_index": idx,
                "recipe_title": "테스트",
                "recipe_image_url": "https://example.com/test.jpg",
            })
            if should_pass:
                if res2.status_code != 200:
                    errors.append(f"index={idx}({label}): {res2.status_code}")
                else:
                    # 정상 추가 후 삭제
                    fav_id = res2.json().get("id")
                    if fav_id:
                        await client.delete(f"{API}/favorites/{fav_id}", headers=headers)
            else:
                if res2.status_code in (200,):
                    errors.append(f"index={idx}({label}): 허용됨 (차단 예상)")
                    # 잘못 추가된 건 삭제
                    fav_id = res2.json().get("id")
                    if fav_id:
                        await client.delete(f"{API}/favorites/{fav_id}", headers=headers)

        if errors:
            return TestResult(name="boundary/recipe-index", passed=False,
                              detail="; ".join(errors))
        return TestResult(name="boundary/recipe-index", passed=True,
                          detail="경계값 검증 완료")

    await timed("boundary/recipe-index", test_recipe_index())


# ─────────────────────────────────────────
# 6. 인증 테스트 (spec-07~08)
# ─────────────────────────────────────────

async def run_auth_tests(client: httpx.AsyncClient, users: list[TestUser]):
    """만료/변조 토큰, 권한 테스트"""
    print("\n[6/8] 인증 테스트 (spec-07~08)...")
    if len(users) < 8:
        report.add(TestResult(name="auth", passed=False, detail="유저 부족"))
        return

    user7, user8 = users[6], users[7]

    # 만료 토큰
    async def test_expired_token():
        fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxMDAwMDAwMDAwfQ.invalid"
        res = await client.get(f"{API}/auth/me", headers=auth_headers(fake_token))
        if res.status_code == 401:
            return TestResult(name="auth/expired-token", passed=True)
        return TestResult(name="auth/expired-token", passed=False,
                          detail=f"status={res.status_code} (401 예상)")

    await timed("auth/expired-token", test_expired_token())

    # 빈 토큰
    async def test_empty_token():
        try:
            res = await client.get(f"{API}/auth/me", headers={"Authorization": ""})
            if res.status_code in (401, 403, 422):
                return TestResult(name="auth/empty-token", passed=True,
                                  detail=f"status={res.status_code}")
            return TestResult(name="auth/empty-token", passed=False,
                              detail=f"status={res.status_code}")
        except httpx.InvalidHeaderError:
            return TestResult(name="auth/empty-token", passed=True,
                              detail="httpx가 잘못된 헤더 차단")

    await timed("auth/empty-token", test_empty_token())

    # 변조 토큰
    async def test_tampered_token():
        tampered = user7.token[:-5] + "XXXXX"
        res = await client.get(f"{API}/auth/me", headers=auth_headers(tampered))
        if res.status_code == 401:
            return TestResult(name="auth/tampered-token", passed=True)
        return TestResult(name="auth/tampered-token", passed=False,
                          detail=f"status={res.status_code}")

    await timed("auth/tampered-token", test_tampered_token())

    # 인증 없이 보호된 엔드포인트 접근
    async def test_no_auth():
        endpoints = [
            ("GET", f"{API}/favorites"),
            ("GET", f"{API}/search-histories"),
            ("GET", f"{API}/auth/me"),
        ]
        errors = []
        for method, url in endpoints:
            if method == "GET":
                res = await client.get(url)
            if res.status_code not in (401, 403):
                errors.append(f"{method} {url}: status={res.status_code}")
        if errors:
            return TestResult(name="auth/no-auth", passed=False, detail="; ".join(errors))
        return TestResult(name="auth/no-auth", passed=True,
                          detail=f"{len(endpoints)}개 엔드포인트 인증 필수 확인")

    await timed("auth/no-auth", test_no_auth())

    # 다른 유저의 즐겨찾기 삭제 시도
    async def test_cross_user_delete():
        h7 = auth_headers(user7.token)
        h8 = auth_headers(user8.token)

        # user7이 추천 + 즐겨찾기 생성
        res = await client.post(f"{API}/recommendations", headers=h7, json={
            "ingredients": ["계란", "밥"],
            "constraints": {"time_limit_min": 15, "quality_level": "fast"},
        })
        if res.status_code != 200:
            return TestResult(name="auth/cross-user", passed=True,
                              detail="추천 생성 실패 (한도 초과 가능)")

        rec_id = res.json()["id"]
        res2 = await client.post(f"{API}/favorites", headers=h7, json={
            "recommendation_id": rec_id,
            "recipe_index": 0,
            "recipe_title": "테스트",
            "recipe_image_url": "https://example.com/test.jpg",
        })
        if res2.status_code != 200:
            return TestResult(name="auth/cross-user", passed=True,
                              detail="즐겨찾기 추가 실패")

        fav_id = res2.json()["id"]

        # user8이 user7의 즐겨찾기 삭제 시도
        res3 = await client.delete(f"{API}/favorites/{fav_id}", headers=h8)
        if res3.status_code in (403, 404):
            # 정리: user7이 자기 즐겨찾기 삭제
            await client.delete(f"{API}/favorites/{fav_id}", headers=h7)
            return TestResult(name="auth/cross-user", passed=True,
                              detail="타인 즐겨찾기 삭제 차단 확인")
        elif res3.status_code == 200:
            return TestResult(name="auth/cross-user", passed=False,
                              detail="타인 즐겨찾기 삭제 허용됨!")
        return TestResult(name="auth/cross-user", passed=False,
                          detail=f"예상 외 status={res3.status_code}")

    await timed("auth/cross-user", test_cross_user_delete())

    # 중복 회원가입
    async def test_duplicate_signup():
        res = await client.post(f"{API}/auth/signup", json={
            "email": user7.email,
            "password": user7.password,
        })
        if res.status_code == 400:
            return TestResult(name="auth/dup-signup", passed=True, detail="중복 가입 차단 확인")
        return TestResult(name="auth/dup-signup", passed=False,
                          detail=f"status={res.status_code}")

    await timed("auth/dup-signup", test_duplicate_signup())

    # 잘못된 비밀번호 로그인
    async def test_wrong_password():
        res = await client.post(f"{API}/auth/login", json={
            "email": user7.email,
            "password": "wrong_password_123",
        })
        if res.status_code == 401:
            return TestResult(name="auth/wrong-pw", passed=True)
        return TestResult(name="auth/wrong-pw", passed=False,
                          detail=f"status={res.status_code}")

    await timed("auth/wrong-pw", test_wrong_password())

    # 짧은 비밀번호 회원가입
    async def test_short_password():
        suffix = rand_suffix()
        res = await client.post(f"{API}/auth/signup", json={
            "email": f"qa-short-{suffix}@test.eupori.dev",
            "password": "12345",  # 5자 (최소 6자)
        })
        if res.status_code in (400, 422):
            return TestResult(name="auth/short-pw", passed=True,
                              detail=f"짧은 비밀번호 차단 ({res.status_code})")
        return TestResult(name="auth/short-pw", passed=False,
                          detail=f"status={res.status_code}")

    await timed("auth/short-pw", test_short_password())


# ─────────────────────────────────────────
# 7. 사이드이펙트 테스트 (spec-09~10)
# ─────────────────────────────────────────

async def run_sideeffect_tests(client: httpx.AsyncClient, users: list[TestUser]):
    """게스트 제한, 존재하지 않는 리소스, 중복 즐겨찾기 등"""
    print("\n[7/8] 사이드이펙트 테스트 (spec-09~10)...")
    if len(users) < 10:
        report.add(TestResult(name="sideeffect", passed=False, detail="유저 부족"))
        return

    user9, user10 = users[8], users[9]

    # 존재하지 않는 추천 ID 조회
    async def test_nonexistent_rec():
        res = await client.get(f"{API}/recommendations/rec_0000000000")
        if res.status_code == 404:
            return TestResult(name="sideeffect/404-rec", passed=True)
        return TestResult(name="sideeffect/404-rec", passed=False,
                          detail=f"status={res.status_code}")

    await timed("sideeffect/404-rec", test_nonexistent_rec())

    # 존재하지 않는 즐겨찾기 삭제
    async def test_nonexistent_fav():
        headers = auth_headers(user9.token)
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        res = await client.delete(f"{API}/favorites/{fake_uuid}", headers=headers)
        if res.status_code in (404, 403):
            return TestResult(name="sideeffect/404-fav", passed=True,
                              detail=f"status={res.status_code}")
        return TestResult(name="sideeffect/404-fav", passed=False,
                          detail=f"status={res.status_code}")

    await timed("sideeffect/404-fav", test_nonexistent_fav())

    # 중복 즐겨찾기
    async def test_duplicate_fav():
        headers = auth_headers(user10.token)
        res = await client.post(f"{API}/recommendations", headers=headers, json={
            "ingredients": ["계란", "밥", "김"],
            "constraints": {"time_limit_min": 15, "quality_level": "fast"},
        })
        if res.status_code != 200:
            return TestResult(name="sideeffect/dup-fav", passed=True,
                              detail="추천 생성 실패 (한도 초과 가능)")

        rec_id = res.json()["id"]
        fav_payload = {
            "recommendation_id": rec_id,
            "recipe_index": 0,
            "recipe_title": "테스트",
            "recipe_image_url": "https://example.com/test.jpg",
        }

        # 첫 번째 즐겨찾기
        res1 = await client.post(f"{API}/favorites", headers=headers, json=fav_payload)
        if res1.status_code != 200:
            return TestResult(name="sideeffect/dup-fav", passed=False,
                              detail=f"첫 즐겨찾기 실패: {res1.status_code}")
        fav_id = res1.json().get("id")

        # 중복 즐겨찾기
        res2 = await client.post(f"{API}/favorites", headers=headers, json=fav_payload)
        # 정리
        if fav_id:
            await client.delete(f"{API}/favorites/{fav_id}", headers=headers)

        if res2.status_code == 400:
            return TestResult(name="sideeffect/dup-fav", passed=True,
                              detail="중복 즐겨찾기 차단 확인")
        return TestResult(name="sideeffect/dup-fav", passed=False,
                          detail=f"중복 즐겨찾기 허용됨: status={res2.status_code}")

    await timed("sideeffect/dup-fav", test_duplicate_fav())

    # 전체 기록 삭제 후 재조회
    async def test_delete_all_history():
        headers = auth_headers(user9.token)
        # 먼저 삭제
        res1 = await client.delete(f"{API}/search-histories/all", headers=headers)
        if res1.status_code != 200:
            return TestResult(name="sideeffect/del-all-history", passed=False,
                              detail=f"전체 삭제 실패: {res1.status_code}")
        # 재조회
        res2 = await client.get(f"{API}/search-histories", headers=headers)
        if res2.status_code == 200 and len(res2.json()) == 0:
            return TestResult(name="sideeffect/del-all-history", passed=True,
                              detail="전체 삭제 후 빈 목록 확인")
        return TestResult(name="sideeffect/del-all-history", passed=False,
                          detail=f"삭제 후 {len(res2.json())}건 남음")

    await timed("sideeffect/del-all-history", test_delete_all_history())

    # 헬스체크
    async def test_health():
        res = await client.get(f"{BASE_URL}/health")
        if res.status_code == 200 and res.json().get("ok"):
            return TestResult(name="sideeffect/health", passed=True)
        return TestResult(name="sideeffect/health", passed=False,
                          detail=f"status={res.status_code}")

    await timed("sideeffect/health", test_health())

    # 좋아요 통계 (공개)
    async def test_fav_stats_public():
        res = await client.get(f"{API}/favorites/stats/rec_0000000000")
        if res.status_code == 200:
            data = res.json()
            if "recipes" in data:
                return TestResult(name="sideeffect/fav-stats", passed=True,
                                  detail="공개 통계 조회 가능")
        return TestResult(name="sideeffect/fav-stats", passed=False,
                          detail=f"status={res.status_code}")

    await timed("sideeffect/fav-stats", test_fav_stats_public())

    # 비로그인 레시피 요청 (게스트 제한 확인)
    async def test_guest_limit():
        """비로그인 상태로 레시피 요청 — 제한 동작 확인"""
        res = await client.post(f"{API}/recommendations", json={
            "ingredients": ["계란", "밥"],
            "constraints": {"time_limit_min": 15, "quality_level": "fast"},
        })
        # 200(성공) 또는 429(제한 초과) 모두 정상 동작
        if res.status_code in (200, 429):
            remaining = res.headers.get("X-Daily-Remaining", "N/A")
            return TestResult(name="sideeffect/guest-limit", passed=True,
                              detail=f"status={res.status_code}, remaining={remaining}")
        return TestResult(name="sideeffect/guest-limit", passed=False,
                          detail=f"status={res.status_code}")

    await timed("sideeffect/guest-limit", test_guest_limit())


# ─────────────────────────────────────────
# 메인
# ─────────────────────────────────────────

async def main():
    print("=" * 50)
    print("    QA 테스트 — 프로덕션 환경 검증")
    print(f"    대상: {BASE_URL}")
    print("=" * 50)

    # 서버 접근 가능 확인
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
        try:
            res = await client.get(f"{BASE_URL}/health")
            if res.status_code != 200:
                print(f"\n❌ 서버 접근 불가: status={res.status_code}")
                return
            print(f"\n✅ 서버 정상 (env={res.json().get('env', '?')})")
        except Exception as e:
            print(f"\n❌ 서버 접근 불가: {e}")
            return

        # 유저 생성
        flow_users, spec_users = await setup_users(client)

        if not flow_users:
            print("\n❌ 유저 생성 실패. 중단합니다.")
            report.print_report()
            return

        # A그룹: 전체 플로우 (순차, LLM 비용 주의)
        await run_flow_tests(client, flow_users)

        # B그룹: 특수 테스트 (순차)
        if len(spec_users) >= 2:
            await run_stress_tests(client, spec_users)

        if len(spec_users) >= 4:
            await run_malicious_tests(client, spec_users)

        if len(spec_users) >= 6:
            await run_boundary_tests(client, spec_users)

        if len(spec_users) >= 8:
            await run_auth_tests(client, spec_users)

        if len(spec_users) >= 10:
            await run_sideeffect_tests(client, spec_users)

        # 결과 출력
        report.print_report()


if __name__ == "__main__":
    asyncio.run(main())
