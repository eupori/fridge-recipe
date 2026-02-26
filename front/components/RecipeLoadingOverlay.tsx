"use client";

import { useState, useEffect, useRef } from "react";
import { ChefHat, X } from "lucide-react";
import { Button } from "@/components/ui/button";

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
  // 추가 퀴즈 20개
  {
    question: "고추의 매운맛을 줄이려면?",
    options: ["씨를 제거한다", "물에 담근다", "냉동한다"],
    answerIndex: 0,
    explanation: "씨와 태좌에 캡사이신이 집중되어 있어요",
  },
  {
    question: "콩나물국 끓일 때 뚜껑을 열면 안 되는 이유는?",
    options: ["비린내가 남아서", "영양이 빠져서", "빨리 식어서"],
    answerIndex: 0,
    explanation: "뚜껑을 열면 비린내가 빠지지 않고 남아요",
  },
  {
    question: "생선 비린내를 잡는 대표적인 재료는?",
    options: ["레몬즙", "식초", "생강"],
    answerIndex: 2,
    explanation: "생강의 향 성분이 비린내를 효과적으로 잡아줘요",
  },
  {
    question: "숙주나물을 아삭하게 데치는 시간은?",
    options: ["10초", "30초", "2분"],
    answerIndex: 1,
    explanation: "30초면 아삭한 식감을 유지하면서 익혀요",
  },
  {
    question: "국물 요리에 주로 사용하는 간장은?",
    options: ["진간장", "국간장", "양조간장"],
    answerIndex: 1,
    explanation: "국간장은 색이 연하고 짠맛이 강해 국물에 적합해요",
  },
  {
    question: "김밥 밥에 참기름을 넣는 이유는?",
    options: ["맛을 위해", "밥알이 안 붙게", "색깔을 위해"],
    answerIndex: 1,
    explanation: "참기름이 밥알 사이를 코팅해 달라붙지 않아요",
  },
  {
    question: "전을 바삭하게 부치는 비결은?",
    options: ["기름을 많이 넣기", "반죽을 얇게 펴기", "센 불로 빠르게"],
    answerIndex: 1,
    explanation: "반죽을 얇게 펴면 수분이 빠르게 증발해 바삭해요",
  },
  {
    question: "냉동 고기를 해동하는 가장 좋은 방법은?",
    options: ["전자레인지", "흐르는 물", "냉장실 해동"],
    answerIndex: 2,
    explanation: "냉장실에서 천천히 해동하면 육즙 손실이 적어요",
  },
  {
    question: "찌개와 국의 가장 큰 차이는?",
    options: ["국이 더 진하다", "찌개가 건더기 위주", "조리 온도가 다르다"],
    answerIndex: 1,
    explanation: "찌개는 건더기 위주, 국은 국물 위주예요",
  },
  {
    question: "높은 온도 조리에 더 적합한 기름은?",
    options: ["식용유", "올리브유", "들기름"],
    answerIndex: 0,
    explanation: "식용유는 발연점이 높아 튀김이나 볶음에 적합해요",
  },
  {
    question: "팥을 삶을 때 첫 물을 버리는 이유는?",
    options: ["사포닌 제거", "색을 예쁘게", "더 빨리 익으라고"],
    answerIndex: 0,
    explanation: "첫 물에 사포닌과 떫은맛 성분이 빠져나와요",
  },
  {
    question: "미역국을 끓일 때 미역을 먼저 볶는 이유는?",
    options: ["식감을 위해", "감칠맛을 위해", "색을 위해"],
    answerIndex: 1,
    explanation: "기름에 볶으면 감칠맛이 더 깊어져요",
  },
  {
    question: "계란찜을 부드럽게 만드는 비결은?",
    options: ["물을 1:1로 넣기", "우유를 넣기", "센 불로 빠르게"],
    answerIndex: 0,
    explanation: "계란과 물을 1:1로 넣으면 부드러운 찜이 돼요",
  },
  {
    question: "고구마를 가장 달게 먹는 조리법은?",
    options: ["삶기", "찌기", "굽기"],
    answerIndex: 2,
    explanation: "천천히 구우면 전분이 당으로 변해 더 달아요",
  },
  {
    question: "양배추를 칼 대신 손으로 찢으면 좋은 이유는?",
    options: ["양념이 잘 배서", "세포 파괴가 적어서", "모양이 예뻐서"],
    answerIndex: 1,
    explanation: "세포 파괴가 적어 쓴맛이 덜 나요",
  },
  {
    question: "볶음밥을 맛있게 하는 핵심은?",
    options: ["센 불 + 빠르게", "약불 + 천천히", "중불 + 뚜껑"],
    answerIndex: 0,
    explanation: "센 불에서 빠르게 볶아야 감칠맛이 살아요",
  },
  {
    question: "국수를 삶은 후 찬물에 헹구는 이유는?",
    options: ["전분 제거", "맛을 위해", "빨리 식히려고"],
    answerIndex: 0,
    explanation: "전분을 씻어내면 면이 쫄깃하고 안 불어요",
  },
  {
    question: "밀가루 반죽을 숙성시키는 이유는?",
    options: ["글루텐 이완", "발효", "수분 증발"],
    answerIndex: 0,
    explanation: "글루텐이 이완되어 반죽이 부드러워져요",
  },
  {
    question: "쌈장과 된장의 차이는?",
    options: ["된장이 더 짜다", "쌈장에 고추장이 섞임", "같은 것이다"],
    answerIndex: 1,
    explanation: "쌈장은 된장에 고추장, 참기름 등을 섞어 만들어요",
  },
  {
    question: "무를 갈아서 고기 재울 때 효과는?",
    options: ["색이 예뻐진다", "고기가 부드러워진다", "보관이 오래된다"],
    answerIndex: 1,
    explanation: "무의 효소가 단백질을 분해해 고기를 연하게 해요",
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

function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

interface RecipeLoadingOverlayProps {
  loading: boolean;
  onDismiss?: () => void;
}

export default function RecipeLoadingOverlay({ loading, onDismiss }: RecipeLoadingOverlayProps) {
  const [elapsed, setElapsed] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Quiz state
  const [quizOrder, setQuizOrder] = useState<number[]>([]);
  const [currentQuiz, setCurrentQuiz] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [score, setScore] = useState(0);
  const [fading, setFading] = useState(false);

  // Dismiss 버튼 표시 여부 (10초 후)
  const [showDismiss, setShowDismiss] = useState(false);

  // Elapsed timer
  useEffect(() => {
    if (!loading) {
      setElapsed(0);
      setShowDismiss(false);
      return;
    }
    setElapsed(0);
    setShowDismiss(false);
    intervalRef.current = setInterval(() => {
      setElapsed((prev) => prev + 0.5);
    }, 500);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [loading]);

  // 10초 후 닫기 버튼 표시
  useEffect(() => {
    if (!loading) return;
    const timer = setTimeout(() => setShowDismiss(true), 10000);
    return () => clearTimeout(timer);
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

        {/* Timer + estimated time */}
        <div className="flex items-center justify-center gap-3 text-sm text-muted-foreground">
          <span>{formatElapsed(elapsed)} 경과</span>
          <span className="text-border">|</span>
          <span>보통 1~2분 소요</span>
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

        {/* Dismiss button (10초 후 표시) */}
        {showDismiss && onDismiss && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onDismiss}
            className="text-muted-foreground hover:text-foreground"
          >
            <X className="w-4 h-4 mr-1" />
            닫고 둘러보기
          </Button>
        )}
      </div>
    </div>
  );
}
