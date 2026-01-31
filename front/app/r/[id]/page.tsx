"use client";

import { useEffect, useState } from "react";
import { getRecommendation } from "../../../lib/api";

export default function ResultPage({ params }: { params: { id: string } }) {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const rec = await getRecommendation(params.id);
        setData(rec);
      } catch (e: any) {
        setError(e?.message ?? "불러오기에 실패했습니다");
      }
    })();
  }, [params.id]);

  if (error) return <main style={{ maxWidth: 760, margin: "40px auto", padding: 16 }}><p style={{ color: "#b00020" }}>{error}</p></main>;
  if (!data) return <main style={{ maxWidth: 760, margin: "40px auto", padding: 16 }}><p>불러오는 중…</p></main>;

  return (
    <main style={{ maxWidth: 760, margin: "40px auto", padding: 16 }}>
      <a href="/" style={{ color: "#111" }}>← 다시 입력</a>
      <h1 style={{ fontSize: 24, fontWeight: 800, marginTop: 12 }}>추천 결과</h1>
      <p style={{ color: "#666" }}>ID: {data.id}</p>

      <section style={{ marginTop: 18, display: "grid", gap: 12 }}>
        {data.recipes?.map((r: any, idx: number) => (
          <article key={idx} style={{ border: "1px solid #eee", borderRadius: 12, padding: 14 }}>
            <h2 style={{ fontSize: 18, fontWeight: 800 }}>{r.title}</h2>
            <div style={{ color: "#666", marginTop: 4 }}>{r.time_min}분 · {r.servings}인분</div>

            {r.image_url ? (
              <img
                src={r.image_url}
                alt={r.title}
                style={{ marginTop: 10, width: "100%", height: 220, objectFit: "cover", borderRadius: 10, background: "#f3f3f3" }}
              />
            ) : null}

            <p style={{ marginTop: 10 }}>{r.summary}</p>

            <div style={{ marginTop: 10 }}>
              <div style={{ fontWeight: 700 }}>총 재료</div>
              <div style={{ color: "#444" }}>{(r.ingredients_total || []).join(", ") || "-"}</div>
            </div>
            <div style={{ marginTop: 10 }}>
              <div style={{ fontWeight: 700 }}>보유 재료(입력 기준)</div>
              <div style={{ color: "#444" }}>{(r.ingredients_have || []).join(", ") || "-"}</div>
            </div>
            <div style={{ marginTop: 10 }}>
              <div style={{ fontWeight: 700 }}>추가 재료</div>
              <div style={{ color: "#444" }}>{(r.ingredients_need || []).join(", ") || "-"}</div>
            </div>

            <ol style={{ marginTop: 10, paddingLeft: 18 }}>
              {(r.steps || []).map((s: string, i: number) => (
                <li key={i} style={{ marginTop: 6 }}>{s}</li>
              ))}
            </ol>

            {r.tips?.length ? (
              <div style={{ marginTop: 10, color: "#555" }}>
                <div style={{ fontWeight: 700 }}>팁</div>
                <ul style={{ marginTop: 6, paddingLeft: 18 }}>
                  {r.tips.map((t: string, i: number) => <li key={i}>{t}</li>)}
                </ul>
              </div>
            ) : null}
          </article>
        ))}
      </section>

      <section style={{ marginTop: 18, borderTop: "1px solid #eee", paddingTop: 14 }}>
        <h2 style={{ fontSize: 18, fontWeight: 800 }}>장보기 리스트</h2>
        <ul style={{ marginTop: 10, paddingLeft: 18 }}>
          {(data.shopping_list || []).map((it: any, idx: number) => (
            <li key={idx} style={{ marginTop: 6 }}>{it.item}</li>
          ))}
        </ul>
      </section>
    </main>
  );
}
