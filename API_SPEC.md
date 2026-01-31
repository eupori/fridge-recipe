# API_SPEC (Draft)

Base: `/api/v1`

## POST `/recommendations`
### Request
```json
{
  "ingredients": ["계란", "김치", "양파", "두부"],
  "constraints": {
    "time_limit_min": 15,
    "servings": 1,
    "tools": ["프라이팬", "전자레인지"],
    "exclude": ["우유", "땅콩"]
  }
}
```

### Response
```json
{
  "id": "rec_abc123",
  "created_at": "2026-01-31T12:00:00+09:00",
  "recipes": [
    {
      "title": "김치두부 스크램블",
      "time_min": 12,
      "servings": 1,
      "summary": "프라이팬 하나로 끝나는 초간단 단백질 한 끼",
      "ingredients_have": ["김치", "두부", "양파", "계란"],
      "ingredients_need": ["식용유"],
      "steps": [
        "양파를 얇게 썰어 1분 볶아요.",
        "김치를 넣고 2분 더 볶아요.",
        "두부를 으깨 넣고 3분 볶아요.",
        "계란을 풀어 넣고 2분 저어 익혀요."
      ],
      "tips": ["김치가 짜면 간장은 생략해요."],
      "warnings": []
    }
  ],
  "shopping_list": [
    {"item": "식용유", "qty": 1, "unit": "병", "category": "양념/오일"}
  ]
}
```

## GET `/recommendations/{id}`
- 목적: 공유/재방문
- 응답: POST와 동일

## Validation rules (server-side)
- recipes 길이=3
- 각 recipe.time_min <= constraints.time_limit_min
- exclude 포함 시 실패 처리 후 재생성(최대 N)
- steps 4~8개, 각 1문장
