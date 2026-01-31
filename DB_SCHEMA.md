# DB_SCHEMA (Draft)

## tables

### recommendations
- id (pk, text/uuid)
- created_at (timestamptz)
- ingredients (jsonb) — 입력 재료 리스트
- constraints (jsonb)
- result (jsonb) — recipes + shopping_list 원본
- model_meta (jsonb) — model, tokens, latency 등
- status (text) — success|error
- error (text, nullable)

### events (optional)
- id (pk)
- created_at
- recommendation_id (fk)
- event_type (text) — create|view|coupang_click
- meta (jsonb)

> MVP는 recommendations 하나만으로도 시작 가능.
