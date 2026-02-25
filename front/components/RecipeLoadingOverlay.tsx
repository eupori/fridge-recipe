"use client";

import { useState, useEffect, useRef } from "react";
import { ChefHat } from "lucide-react";

const STANDARD_STAGES = [
  { until: 3, message: "AI가 재료 조합을 분석 중...", progress: 15 },
  { until: 8, message: "맞춤 레시피를 구성 중...", progress: 35 },
  { until: 13, message: "레시피 이미지 생성 중...", progress: 55 },
  { until: 18, message: "장보기 리스트 정리 중...", progress: 75 },
  { until: Infinity, message: "거의 다 됐어요! 마무리 중...", progress: 90 },
];

type Quiz = {
  question: string;
  options: string[];
  answerIndex: number;
  explanation: string;
};

const QUIZ_POOL: Quiz[] = [
  {
    question: "김치볶음밥에 가장 적합한 밥은?",
    options: ["갓 지은 밥", "찬밥", "즉석밥"],
    answerIndex: 1,
    explanation: "수분이 적어 파라파라하게 볶아져요",
  },
  {
    question: "달걀을 삶을 때 식초를 넣는 이유는?",
    options: ["빨리 익으라고", "껍질이 안 깨지게", "흰자 응고 촉진"],
    answerIndex: 2,
    explanation: "식초가 단백질 응고를 도와 흰자 유출을 막아요",
  },
  {
    question: "양파를 오래 볶으면 단맛이 나는 이유는?",
    options: ["설탕 첨가", "캐러멜화 반응", "수분 증발"],
    answerIndex: 1,
    explanation: "당분이 열에 의해 캐러멜화되면서 단맛이 강해져요",
  },
  {
    question: "파스타 삶을 때 기름을 넣으면?",
    options: ["면이 안 붙는다", "소스가 안 묻는다"],
    answerIndex: 1,
    explanation: "기름 막이 생겨 소스가 면에 잘 배지 않아요",
  },
  {
    question: "고기를 구울 때 자주 뒤집으면?",
    options: ["더 빨리 익는다", "육즙이 빠진다", "골고루 익는다"],
    answerIndex: 1,
    explanation: "자주 뒤집으면 육즙이 빠져 퍽퍽해져요",
  },
  {
    question: "감자는 어떤 물에서부터 삶아야 할까요?",
    options: ["찬물", "끓는 물", "미지근한 물"],
    answerIndex: 0,
    explanation: "찬물부터 삶아야 속까지 고르게 익어요",
  },
  {
    question: "참기름은 언제 넣어야 할까요?",
    options: ["처음부터", "중간에", "불 끄고 마지막에"],
    answerIndex: 2,
    explanation: "열에 의해 향이 날아가므로 마지막에 넣어요",
  },
  {
    question: "된장찌개를 끓일 때 된장은 언제 넣나요?",
    options: ["처음부터", "물이 끓은 후", "불 끄기 직전"],
    answerIndex: 1,
    explanation: "물이 끓은 후 풀어야 깔끔하게 녹아요",
  },
  {
    question: "라면 물의 황금비율은?",
    options: ["350ml", "550ml", "750ml"],
    answerIndex: 1,
    explanation: "550ml가 면과 스프의 맛이 가장 잘 어우러져요",
  },
  {
    question: "두부를 부치기 전에 해야 할 것은?",
    options: ["소금에 절이기", "물기 제거하기", "냉동하기"],
    answerIndex: 1,
    explanation: "키친타올로 물기를 빼면 잘 부서지지 않아요",
  },
  {
    question: "마늘을 볶을 때 주의할 점은?",
    options: ["큰 불에서 빨리 볶기", "약한 불에서 천천히 볶기", "기름 없이 볶기"],
    answerIndex: 1,
    explanation: "센 불에서 볶으면 쓴맛이 나요",
  },
  {
    question: "카레가 가장 맛있는 때는?",
    options: ["바로 만들었을 때", "하루 지났을 때", "3일 후"],
    answerIndex: 1,
    explanation: "하루 숙성되면 재료의 맛이 더 어우러져요",
  },
  {
    question: "생선 구울 때 어느 면부터 구워야 할까요?",
    options: ["껍질 면", "살 면", "상관없다"],
    answerIndex: 0,
    explanation: "껍질부터 구우면 모양이 예쁘게 유지돼요",
  },
  {
    question: "나물 데칠 때 소금을 넣는 이유는?",
    options: ["간을 맞추려고", "색이 선명해지게", "빨리 익으라고"],
    answerIndex: 1,
    explanation: "소금이 엽록소를 보호해 초록색이 유지돼요",
  },
  {
    question: "볶음 요리에서 채소를 넣는 순서는?",
    options: ["작은 것부터", "큰 것부터", "동시에"],
    answerIndex: 1,
    explanation: "큰 채소가 오래 걸리니 먼저 넣어야 고르게 익어요",
  },
  {
    question: "밥을 지을 때 물 양의 기준은?",
    options: ["쌀과 동량", "쌀의 1.2배", "쌀의 1.5배"],
    answerIndex: 1,
    explanation: "쌀 대비 1.2배의 물이 적당한 밥을 만들어요",
  },
  {
    question: "고추장을 볶으면 어떤 변화가 생길까요?",
    options: ["매워진다", "감칠맛이 올라간다", "색이 변한다"],
    answerIndex: 1,
    explanation: "볶으면 발효 향이 살아나고 감칠맛이 깊어져요",
  },
  {
    question: "계란 프라이를 부칠 때 뚜껑을 덮으면?",
    options: ["노른자가 터진다", "윗면도 익는다", "맛이 없어진다"],
    answerIndex: 1,
    explanation: "증기로 윗면이 익어 반숙을 만들기 좋아요",
  },
  {
    question: "국물 요리의 기본 불 조절은?",
    options: ["계속 센 불", "계속 약한 불", "센 불로 끓인 후 약불"],
    answerIndex: 2,
    explanation: "센 불로 끓인 후 약불로 줄여야 맛이 우러나요",
  },
  {
    question: "버터는 냉장고 어디에 보관해야 할까요?",
    options: ["냉동실", "냉장실 문 쪽", "냉장실 안쪽"],
    answerIndex: 2,
    explanation: "문 쪽은 온도 변화가 커서 안쪽이 좋아요",
  },
];

function shuffleIndices(length: number): number[] {
  const arr = Array.from({ length }, (_, i) => i);
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

interface RecipeLoadingOverlayProps {
  loading: boolean;
}

export default function RecipeLoadingOverlay({ loading }: RecipeLoadingOverlayProps) {
  const [elapsed, setElapsed] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Quiz state
  const [quizOrder, setQuizOrder] = useState<number[]>([]);
  const [currentQuiz, setCurrentQuiz] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [score, setScore] = useState(0);
  const [fading, setFading] = useState(false);

  // Elapsed timer
  useEffect(() => {
    if (!loading) {
      setElapsed(0);
      return;
    }
    setElapsed(0);
    intervalRef.current = setInterval(() => {
      setElapsed((prev) => prev + 0.5);
    }, 500);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [loading]);

  // Quiz initialization
  useEffect(() => {
    if (!loading) return;
    setQuizOrder(shuffleIndices(QUIZ_POOL.length));
    setCurrentQuiz(0);
    setSelected(null);
    setScore(0);
    setFading(false);
  }, [loading]);

  // Auto-advance after answer
  useEffect(() => {
    if (selected === null) return;
    const timer = setTimeout(() => {
      setFading(true);
      setTimeout(() => {
        setCurrentQuiz((prev) => prev + 1);
        setSelected(null);
        setFading(false);
      }, 300);
    }, 1500);
    return () => clearTimeout(timer);
  }, [selected]);

  if (!loading) return null;

  const stages = STANDARD_STAGES;
  const stage = stages.find((s) => elapsed < s.until) ?? stages[stages.length - 1];

  const quizIndex = quizOrder[currentQuiz];
  const quiz = quizIndex !== undefined ? QUIZ_POOL[quizIndex] : null;
  const answered = currentQuiz; // number of questions answered

  const handleSelect = (optionIdx: number) => {
    if (selected !== null) return; // already answered
    setSelected(optionIdx);
    if (quiz && optionIdx === quiz.answerIndex) {
      setScore((s) => s + 1);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm" role="alert" aria-live="assertive">
      <div className="flex flex-col items-center gap-6 px-6 w-full max-w-sm text-center">
        {/* Animated icon */}
        <ChefHat className="w-14 h-14 text-primary animate-bounce" />

        {/* Stage message */}
        <p className="text-lg font-medium text-foreground">{stage.message}</p>

        {/* Progress bar */}
        <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
          <div
            className="h-full bg-primary rounded-full transition-all duration-1000 ease-out"
            style={{ width: `${stage.progress}%` }}
          />
        </div>

        {/* Divider */}
        <div className="w-full border-t border-border" />

        {/* Quiz section */}
        {quiz ? (
          <div className={`w-full space-y-3 transition-opacity duration-300 ${fading ? "opacity-0" : "opacity-100"}`}>
            <p className="text-sm font-medium text-foreground">{quiz.question}</p>
            <div className="grid gap-2">
              {quiz.options.map((option, idx) => {
                let btnClass = "w-full text-left px-3 py-2 rounded-lg border text-sm transition-colors ";
                if (selected === null) {
                  btnClass += "hover:bg-muted cursor-pointer border-border";
                } else if (idx === quiz.answerIndex) {
                  btnClass += "bg-green-100 dark:bg-green-900/30 border-green-500 text-green-700 dark:text-green-300";
                } else if (idx === selected) {
                  btnClass += "bg-red-100 dark:bg-red-900/30 border-red-500 text-red-700 dark:text-red-300";
                } else {
                  btnClass += "opacity-50 border-border";
                }

                return (
                  <button
                    key={idx}
                    className={btnClass}
                    onClick={() => handleSelect(idx)}
                    disabled={selected !== null}
                  >
                    {option}
                  </button>
                );
              })}
            </div>
            {selected !== null && (
              <p className="text-xs text-muted-foreground mt-1">
                {selected === quiz.answerIndex ? "⭕ " : "❌ "}
                {quiz.explanation}
              </p>
            )}
            {answered > 0 && (
              <p className="text-xs text-muted-foreground">
                {score}/{answered} 맞힘
              </p>
            )}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">모든 퀴즈를 풀었어요! 🎉</p>
        )}
      </div>
    </div>
  );
}
