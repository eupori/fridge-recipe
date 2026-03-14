"""단일 케이스 테스트 - 타임아웃/JSON 잘림 디버깅"""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, ".")

from app.models.recommendation import Constraints, RecommendationCreate
from app.services.llm_adapter import RecipeLLMAdapter

ingredients = sys.argv[1].split(",") if len(sys.argv) > 1 else ["파스타면", "베이컨", "마늘", "올리브오일"]

payload = RecommendationCreate(
    ingredients=ingredients,
    constraints=Constraints(time_limit_min=15, servings=1),
)
adapter = RecipeLLMAdapter()
sp = adapter._build_system_prompt()
up = adapter._build_user_prompt(payload)

env = os.environ.copy()
env.pop("CLAUDECODE", None)
cmd = [
    "claude", "-p", up,
    "--system-prompt", sp,
    "--output-format", "text",
    "--max-turns", "1",
    "--model", "sonnet",
    "--no-session-persistence",
]

start = time.monotonic()
try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)
    elapsed = time.monotonic() - start
    print(f"returncode: {result.returncode} ({elapsed:.1f}s)")
    print(f"stdout: {len(result.stdout)} chars")
    if result.stderr:
        print(f"stderr: {result.stderr[:300]}")

    stdout = result.stdout.strip()
    # JSON 추출
    if "```json" in stdout:
        s = stdout.find("```json") + 7
        e = stdout.find("```", s)
        json_str = stdout[s:e].strip()
    elif "```" in stdout:
        s = stdout.find("```") + 3
        e = stdout.find("```", s)
        json_str = stdout[s:e].strip()
    else:
        json_str = stdout

    data = json.loads(json_str)
    print(f"JSON OK: {len(data)}개 레시피")
    for r in data:
        print(f"  - {r['title']} ({r['time_min']}분) | {r.get('summary','')}")
except subprocess.TimeoutExpired:
    elapsed = time.monotonic() - start
    print(f"TIMEOUT after {elapsed:.1f}s")
except json.JSONDecodeError as e:
    print(f"JSON 파싱 실패: {e}")
    print(f"전체 응답:\n{result.stdout}")
except Exception as e:
    print(f"ERROR: {e}")
