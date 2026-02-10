# AWS 배포 가이드: Lambda + Vercel + Supabase

## 아키텍처

```
[Vercel]                    [AWS Lambda + API Gateway]
Next.js 프론트엔드    ←→    FastAPI 백엔드 (Mangum)
     ↓                              ↓
NEXT_PUBLIC_API_BASE        DATABASE_URL
                                    ↓
                          [Supabase PostgreSQL]
```

**예상 비용:**
- Lambda: 월 100만 요청 무료, 이후 $0.20/100만 요청
- Vercel: 무료 티어 (개인 프로젝트)
- Supabase: 무료 티어 (500MB DB)

---

## 1단계: Supabase 설정

### 1.1 프로젝트 생성
1. https://supabase.com 접속 → 새 프로젝트 생성
2. Region: `ap-northeast-2` (서울) 선택
3. Database Password 설정 (저장 필수)

### 1.2 Connection String 획득
- Settings → Database → Connection string → URI 복사
- SQLAlchemy용 형식으로 변환:
  ```
  postgresql+psycopg://postgres.[project-ref]:[password]@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres
  ```

### 1.3 테이블 생성
Supabase SQL Editor에서 실행:
```sql
-- UUID 확장 활성화
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    nickname VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Favorites table
CREATE TABLE IF NOT EXISTS favorites (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    recommendation_id VARCHAR(50) NOT NULL,
    recipe_index INTEGER NOT NULL,
    recipe_title VARCHAR(200) NOT NULL,
    recipe_image_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_favorites_user_id ON favorites(user_id);

-- Search history table
CREATE TABLE IF NOT EXISTS search_histories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    recommendation_id VARCHAR(50) NOT NULL,
    ingredients JSONB NOT NULL,
    time_limit_min INTEGER NOT NULL,
    servings INTEGER NOT NULL,
    recipe_titles JSONB NOT NULL,
    recipe_images JSONB,
    searched_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_search_histories_user_id ON search_histories(user_id);
CREATE INDEX IF NOT EXISTS idx_search_histories_searched_at ON search_histories(searched_at DESC);
```

---

## 2단계: AWS Lambda 배포 (SAM)

### 2.1 사전 요구사항
```bash
# AWS CLI 설치 및 설정
aws configure

# AWS SAM CLI 설치
brew install aws-sam-cli  # macOS
# 또는 pip install aws-sam-cli
```

### 2.2 빌드 및 배포
```bash
cd back

# 빌드
sam build

# 배포 (첫 실행 시 --guided 사용)
sam deploy --guided
```

**배포 시 설정값:**
```
Stack Name: fridge-recipe-api
Region: ap-northeast-2
Parameter AppEnv: prod
Parameter DatabaseUrl: postgresql+psycopg://...  # Supabase URL
Parameter JwtSecretKey: <강력한-랜덤-문자열>
Parameter CorsOrigins: https://your-app.vercel.app
Parameter AnthropicApiKey: sk-ant-...
Parameter GeminiApiKey: ...
Parameter LlmProvider: anthropic
Parameter ImageSearchProvider: gemini
```

### 2.3 배포 확인
```bash
# API Gateway URL 확인
aws cloudformation describe-stacks \
  --stack-name fridge-recipe-api \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text

# 헬스체크
curl https://YOUR-API-ID.execute-api.ap-northeast-2.amazonaws.com/health
```

---

## 3단계: Vercel 프론트엔드 배포

### 3.1 Vercel 연결
1. https://vercel.com → Import Git Repository
2. `fridge-recipe` 레포 선택
3. Root Directory: `front`
4. Framework Preset: Next.js

### 3.2 환경변수 설정
Vercel Dashboard → Settings → Environment Variables:
```
NEXT_PUBLIC_API_BASE=https://YOUR-API-ID.execute-api.ap-northeast-2.amazonaws.com/api/v1
```

### 3.3 배포
- `main` 브랜치 푸시 → 자동 배포
- 또는: `vercel --prod`

---

## 4단계: CORS 업데이트

Lambda 배포 후 Vercel 도메인으로 CORS 업데이트:
```bash
# SAM parameter 업데이트
sam deploy --parameter-overrides \
  CorsOrigins="https://fridge-recipe.vercel.app,https://your-custom-domain.com"
```

---

## 대안: Serverless Framework

SAM 대신 Serverless Framework 사용:

```bash
cd back

# Serverless 설치
npm install -g serverless
npm install --save-dev serverless-python-requirements

# 환경변수 설정
export DATABASE_URL="postgresql+psycopg://..."
export JWT_SECRET_KEY="..."
export ANTHROPIC_API_KEY="..."
export GEMINI_API_KEY="..."

# 배포
serverless deploy
```

---

## 문제 해결

### Cold Start 최적화
- MemorySize를 512MB 이상으로 설정 (CPU 비례 증가)
- 필요시 Provisioned Concurrency 설정

### 이미지 캐시
Lambda는 파일시스템 쓰기가 제한적이므로:
- `IMAGE_CACHE_ENABLED=false` 설정
- 또는 S3를 캐시 저장소로 사용 (추후 구현)

### 로그 확인
```bash
# CloudWatch 로그
aws logs tail /aws/lambda/fridge-recipe-api --follow
```

### 환경변수 업데이트
```bash
# SAM으로 파라미터 업데이트
sam deploy --parameter-overrides \
  AnthropicApiKey="sk-ant-new-key"
```

---

## 검증 체크리스트

- [ ] Supabase 연결 확인: `/health` 엔드포인트
- [ ] 회원가입/로그인 테스트
- [ ] 레시피 검색 테스트
- [ ] 즐겨찾기 저장/조회 테스트
- [ ] 검색 기록 확인
- [ ] CORS 정상 작동 확인 (브라우저 콘솔)
