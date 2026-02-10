# LLM 통합 빠른 시작 가이드

## 5분 안에 시작하기

### 1단계: 패키지 설치 (1분)
```bash
cd back
pip install -r requirements.txt
```

### 2단계: 환경 설정 (1분)

#### 옵션 A: Mock 모드 (API 키 불필요) ⭐ 추천
```bash
# back/.env 파일 수정
LLM_PROVIDER=mock
```

#### 옵션 B: 실제 Claude API 사용
```bash
# back/.env 파일 수정
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-api-key-here
```

### 3단계: 테스트 (1분)
```bash
cd back
python test_llm_integration.py
```

예상 출력:
```
✅ 레시피 생성 성공! (ID: rec_abc123)

[레시피 1] 김치계란볶음밥
  조리 시간: 12분
  보유 재료 (3개): 계란, 김치, 밥
  ...
```

### 4단계: 서버 실행 (1분)
```bash
uvicorn app.main:app --reload --port 8000
```

### 5단계: API 호출 테스트 (1분)
```bash
curl -X POST http://localhost:8000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "ingredients": ["계란", "김치", "밥"],
    "constraints": {"time_limit_min": 15, "servings": 1}
  }'
```

---

## 개발 워크플로우

### Mock 모드로 개발 (API 비용 0원)
```bash
# .env 설정
LLM_PROVIDER=mock

# 서버 실행
uvicorn app.main:app --reload

# 프론트엔드 테스트
cd ../front
npm run dev
```

### 실제 API로 최종 테스트
```bash
# .env 설정
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...

# 서버 재시작
uvicorn app.main:app --reload
```

---

## 프롬프트 수정하기

### 파일 위치
`back/app/services/llm_adapter.py`

### 시스템 프롬프트 수정
```python
def _build_system_prompt(self) -> str:
    return """당신은 한국 가정 요리 전문 셰프입니다.

규칙:
1. 정확히 3개의 레시피 생성
2. 각 레시피는 4-8개 조리 단계
3. 모든 텍스트는 한국어
...
"""
```

### 사용자 프롬프트 수정
```python
def _build_user_prompt(self, payload: RecommendationCreate) -> str:
    return f"""다음 조건으로 레시피를 생성해주세요:

재료: {ingredients_str}
시간 제한: {time_limit_min}분
...
"""
```

### 테스트
```bash
python test_llm_integration.py
```

---

## 문제 해결 1분 가이드

### ❌ "ANTHROPIC_API_KEY가 설정되지 않았습니다"
```bash
# Mock 모드로 전환
echo "LLM_PROVIDER=mock" >> .env
```

### ❌ "ModuleNotFoundError: No module named 'anthropic'"
```bash
pip install -r requirements.txt
```

### ❌ 레시피가 항상 같음
```bash
# Mock 모드 사용 중 → 정상 동작
# 실제 API 사용:
echo "LLM_PROVIDER=anthropic" >> .env
```

### ❌ JSON 파싱 실패
```bash
# 재시도 로직 동작 중 (최대 2회)
# 로그 확인:
tail -f logs/app.log | grep "LLM"
```

---

## 비용 계산기

### Claude Sonnet 4.5
- 요청당: ~$0.024 (약 30원)
- 100 요청: ~$2.4 (약 3,000원)
- 1000 요청: ~$24 (약 30,000원)

### 비용 절감 팁
1. 개발 중 Mock 모드 사용 (무료)
2. 결과 캐싱 구현 (향후)
3. Prompt Caching 활성화 (향후)

---

## API 키 발급 방법

1. [Anthropic Console](https://console.anthropic.com/) 접속
2. API Keys 메뉴 클릭
3. "Create Key" 버튼 클릭
4. 키 복사 (sk-ant-로 시작)
5. `.env` 파일에 추가:
   ```bash
   ANTHROPIC_API_KEY=sk-ant-복사한-키
   ```

---

## 다음 단계

### 필수
- [ ] Mock 모드로 기능 테스트
- [ ] 프론트엔드 연동 확인
- [ ] 다양한 재료 조합 테스트

### 선택
- [ ] API 키 발급 및 실제 API 테스트
- [ ] 프롬프트 품질 개선
- [ ] 캐싱 구현

---

**상세 문서:** `LLM_INTEGRATION_README.md`
**프로젝트 가이드:** `../CLAUDE.md`
