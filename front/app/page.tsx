"use client";

import { useMemo, useState } from "react";
import { createRecommendation } from "../lib/api";

export default function HomePage() {
  const [ingredientsText, setIngredientsText] = useState("계란, 김치, 양파");
  const [excludeText, setExcludeText] = useState("");
  const [timeLimit, setTimeLimit] = useState(15);
  const [servings, setServings] = useState(1);
  const [tools, setTools] = useState<string[]>(["프라이팬"]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ingredients = useMemo(() => {
    return ingredientsText
      .split(/,|\n/)
      .map((s) => s.trim())
      .filter(Boolean);
  }, [ingredientsText]);

  async function onSubmit() {
    setError(null);
    setLoading(true);
    try {
      const exclude = excludeText
        .split(/,|\n/)
        .map((s) => s.trim())
        .filter(Boolean);

      const rec = await createRecommendation({
        ingredients,
        constraints: {
          time_limit_min: timeLimit,
          servings,
          tools,
          exclude,
        },
      });

      window.location.href = `/r/${rec.id}`;
    } catch (e: any) {
      setError(e?.message ?? "요청에 실패했습니다");
    } finally {
      setLoading(false);
    }
  }

  function toggleTool(t: string) {
    setTools((prev) => (prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]));
  }

  return (
    <main style={{ maxWidth: 760, margin: "40px auto", padding: 16 }}>
      <h1 style={{ fontSize: 28, fontWeight: 700 }}>오늘의 냉장고 레시피 3개</h1>
      <p style={{ color: "#555" }}>재료를 입력하면 15분 내 가능한 레시피 3개와 장보기 리스트를 만들어줘요.</p>

      <section style={{ marginTop: 24 }}>
        <label style={{ display: "block", fontWeight: 600 }}>재료</label>
        <textarea
          value={ingredientsText}
          onChange={(e) => setIngredientsText(e.target.value)}
          rows={5}
          placeholder="예: 계란, 김치, 양파\n두부"
          style={{ width: "100%", marginTop: 8, padding: 12, border: "1px solid #ddd", borderRadius: 8 }}
        />
        <div style={{ marginTop: 8, color: "#666", fontSize: 13 }}>인식된 재료: {ingredients.join(", ") || "(없음)"}</div>
      </section>

      <section style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 16 }}>
        <div>
          <label style={{ display: "block", fontWeight: 600 }}>시간(분)</label>
          <select value={timeLimit} onChange={(e) => setTimeLimit(Number(e.target.value))} style={{ width: "100%", marginTop: 8, padding: 10 }}>
            <option value={10}>10</option>
            <option value={15}>15</option>
            <option value={20}>20</option>
          </select>
        </div>
        <div>
          <label style={{ display: "block", fontWeight: 600 }}>인분</label>
          <select value={servings} onChange={(e) => setServings(Number(e.target.value))} style={{ width: "100%", marginTop: 8, padding: 10 }}>
            <option value={1}>1</option>
            <option value={2}>2</option>
          </select>
        </div>
      </section>

      <section style={{ marginTop: 16 }}>
        <label style={{ display: "block", fontWeight: 600 }}>조리도구</label>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}>
          {[
            "프라이팬",
            "전자레인지",
            "에어프라이어",
          ].map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => toggleTool(t)}
              style={{
                padding: "8px 10px",
                borderRadius: 999,
                border: "1px solid #ddd",
                background: tools.includes(t) ? "#111" : "#fff",
                color: tools.includes(t) ? "#fff" : "#111",
              }}
            >
              {t}
            </button>
          ))}
        </div>
      </section>

      <section style={{ marginTop: 16 }}>
        <label style={{ display: "block", fontWeight: 600 }}>제외 재료/알레르기</label>
        <input
          value={excludeText}
          onChange={(e) => setExcludeText(e.target.value)}
          placeholder="예: 우유, 땅콩"
          style={{ width: "100%", marginTop: 8, padding: 12, border: "1px solid #ddd", borderRadius: 8 }}
        />
      </section>

      {error && <p style={{ marginTop: 12, color: "#b00020" }}>{error}</p>}

      <button
        onClick={onSubmit}
        disabled={loading || ingredients.length === 0}
        style={{
          marginTop: 20,
          width: "100%",
          padding: 14,
          borderRadius: 10,
          background: loading ? "#666" : "#111",
          color: "#fff",
          fontWeight: 700,
          border: "none",
          cursor: "pointer",
        }}
      >
        {loading ? "생성 중…" : "레시피 3개 추천받기"}
      </button>

      <p style={{ marginTop: 10, fontSize: 12, color: "#666" }}>
        MVP: 지금은 백엔드가 더미 응답을 반환하도록 되어 있어요. LLM 연동은 다음 단계에서 붙입니다.
      </p>
    </main>
  );
}
