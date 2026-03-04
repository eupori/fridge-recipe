import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "냉탐정 - 냉장고 재료로 AI 레시피 추천";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          background: "linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)",
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ fontSize: 80, marginBottom: 12, display: "flex" }}>
          🍳
        </div>
        <div
          style={{
            fontSize: 64,
            fontWeight: 800,
            color: "#0f172a",
            marginBottom: 16,
            display: "flex",
          }}
        >
          냉탐정
        </div>
        <div
          style={{
            fontSize: 32,
            fontWeight: 600,
            color: "#3b82f6",
            marginBottom: 24,
            display: "flex",
          }}
        >
          냉장고 열면, 답 나온다
        </div>
        <div
          style={{
            fontSize: 22,
            color: "#64748b",
            display: "flex",
          }}
        >
          AI가 추천하는 15분 레시피 3개 + 장보기 리스트
        </div>
      </div>
    ),
    { ...size }
  );
}
