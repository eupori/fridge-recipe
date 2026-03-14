"""프롬프트 품질 테스트 - 10가지 자취생 재료 세트로 카테고리 다양성 검증"""

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, ".")

from app.models.recommendation import Constraints, RecommendationCreate
from app.services.llm_adapter import RecipeLLMAdapter, parse_llm_response, _call_claude_cli
from app.services.validation import detect_category

TEST_CASES = [
    # 1. 라면 중심 (기존 문제: 라면 3종)
    {"name": "라면+계란+대파+치즈", "ingredients": ["라면", "계란", "대파", "치즈"]},
    # 2. 토스트 중심 (기존 문제: 토스트 3종)
    {"name": "식빵+햄+치즈+버터", "ingredients": ["식빵", "햄", "치즈", "버터"]},
    # 3. 파스타 중심 (기존 문제: 파스타 3종)
    {"name": "파스타면+베이컨+마늘+올리브오일", "ingredients": ["파스타면", "베이컨", "마늘", "올리브오일"]},
    # 4. 자취생 기본 냉장고
    {"name": "계란+김치+두부+대파", "ingredients": ["계란", "김치", "두부", "대파"]},
    # 5. 편의점 장보기
    {"name": "참치캔+밥+김+마요네즈", "ingredients": ["참치캔", "밥", "김", "마요네즈"]},
    # 6. 재료 1개 (극단 케이스)
    {"name": "감자만", "ingredients": ["감자"]},
    # 7. 고기 중심
    {"name": "삼겹살+양파+고추장+상추", "ingredients": ["삼겹살", "양파", "고추장", "상추"]},
    # 8. 야채 중심
    {"name": "양배추+당근+양파+계란", "ingredients": ["양배추", "당근", "양파", "계란"]},
    # 9. 한식 기본
    {"name": "밥+된장+두부+애호박+대파", "ingredients": ["밥", "된장", "두부", "애호박", "대파"]},
    # 10. 양식 재료
    {"name": "토마토+모짜렐라+바질+올리브오일", "ingredients": ["토마토", "모짜렐라", "바질", "올리브오일"]},
]


def _call_cli_clean(system_prompt: str, user_prompt: str, model: str, timeout: int = 120) -> str:
    """CLAUDECODE 환경변수 제거 후 CLI 호출 (로컬 테스트용)"""
    import os, subprocess as sp
    env = os.environ.copy()
    env.pop("CLAUDECODE", None)
    env.setdefault("HOME", os.path.expanduser("~"))
    cmd = [
        "claude", "-p", user_prompt,
        "--system-prompt", system_prompt,
        "--output-format", "text",
        "--max-turns", "1",
        "--model", model,
        "--no-session-persistence",
    ]
    result = sp.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
    if result.returncode != 0:
        raise RuntimeError(f"CLI 실패 (exit={result.returncode}): {result.stderr[:200]}")
    output = result.stdout.strip()
    if not output:
        raise RuntimeError("CLI 응답 비어있음")
    return output


def run_single_test(idx: int, case: dict) -> dict:
    """단일 테스트 실행"""
    payload = RecommendationCreate(
        ingredients=case["ingredients"],
        constraints=Constraints(time_limit_min=15, servings=1),
    )
    adapter = RecipeLLMAdapter()
    system_prompt = adapter._build_system_prompt()
    user_prompt = adapter._build_user_prompt(payload)

    start = time.monotonic()
    try:
        raw = _call_cli_clean(system_prompt, user_prompt, model="sonnet")
        recipes = parse_llm_response(raw)
        elapsed = time.monotonic() - start

        results = []
        for r in recipes:
            title = r.get("title", "?")
            cat = detect_category(title) or "미분류"
            summary = r.get("summary", "")
            results.append({"title": title, "category": cat, "summary": summary})

        cats = [r["category"] for r in results]
        diverse = len(set(c for c in cats if c != "미분류")) >= 2

        return {
            "idx": idx + 1,
            "name": case["name"],
            "elapsed": elapsed,
            "recipes": results,
            "categories": cats,
            "diverse": diverse,
            "error": None,
        }
    except Exception as e:
        return {
            "idx": idx + 1,
            "name": case["name"],
            "elapsed": time.monotonic() - start,
            "recipes": [],
            "categories": [],
            "diverse": False,
            "error": str(e),
        }


def main():
    print("=" * 70)
    print("프롬프트 품질 테스트 (10가지 자취생 재료 세트)")
    print("=" * 70)

    total_start = time.monotonic()

    # 순차 실행 (병렬 시 CLI 리소스 경쟁으로 타임아웃 발생)
    results = [None] * len(TEST_CASES)
    for i, case in enumerate(TEST_CASES):
        r = run_single_test(i, case)
        results[i] = r
        if r["error"]:
            print(f"  [{r['idx']:2d}/10] {r['name']} — ERROR: {r['error'][:80]}")
        else:
            status = "✅" if r["diverse"] else "❌"
            cats_str = " / ".join(r["categories"])
            print(f"  [{r['idx']:2d}/10] {r['name']} — {status} {cats_str} ({r['elapsed']:.1f}s)")

    total_elapsed = time.monotonic() - total_start
    print()
    print("=" * 70)
    print("상세 결과")
    print("=" * 70)

    pass_count = 0
    for r in results:
        if not r:
            continue
        status = "✅ 다양" if r["diverse"] else "❌ 중복"
        print(f"\n[{r['idx']}] {r['name']} — {status}")
        if r["error"]:
            print(f"   ERROR: {r['error'][:100]}")
            continue
        for i, recipe in enumerate(r["recipes"], 1):
            print(f"   {i}. {recipe['title']} [{recipe['category']}]")
            print(f"      → {recipe['summary']}")
        if r["diverse"]:
            pass_count += 1

    print()
    print("=" * 70)
    print(f"결과: {pass_count}/{len(TEST_CASES)} 통과 (카테고리 다양성)")
    print(f"총 소요시간: {total_elapsed:.1f}초")
    print("=" * 70)


if __name__ == "__main__":
    main()
