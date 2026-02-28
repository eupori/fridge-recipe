"use client";

import { createContext, useContext, useState, useCallback, useEffect, useRef, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { getJobStatus } from "./api";

interface RecipeJobState {
  isProcessing: boolean;
  jobId: string | null;
  progress: number;
  error: string | null;
}

interface RecipeJobContextType extends RecipeJobState {
  startJob: (jobId: string) => void;
  clearJob: () => void;
}

const RecipeJobContext = createContext<RecipeJobContextType | null>(null);

const TIMEOUT_MS = 180_000; // 3분
const JOB_STORAGE_KEY = "active-job-id";

function saveJobId(jobId: string) {
  try {
    localStorage.setItem(JOB_STORAGE_KEY, jobId);
    sessionStorage.setItem(JOB_STORAGE_KEY, jobId);
  } catch { /* storage unavailable */ }
}

function loadJobId(): string | null {
  try {
    return sessionStorage.getItem(JOB_STORAGE_KEY) || localStorage.getItem(JOB_STORAGE_KEY);
  } catch { return null; }
}

function clearJobId() {
  try {
    sessionStorage.removeItem(JOB_STORAGE_KEY);
    localStorage.removeItem(JOB_STORAGE_KEY);
  } catch { /* storage unavailable */ }
}

export function RecipeJobProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [state, setState] = useState<RecipeJobState>({
    isProcessing: false,
    jobId: null,
    progress: 0,
    error: null,
  });
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number>(0);
  const pollErrorCount = useRef(0);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const poll = useCallback(
    (jobId: string) => {
      startTimeRef.current = Date.now();
      pollErrorCount.current = 0;

      intervalRef.current = setInterval(async () => {
        // 타임아웃 체크
        if (Date.now() - startTimeRef.current > TIMEOUT_MS) {
          stopPolling();
          clearJobId();
          setState((prev) => ({
            ...prev,
            isProcessing: false,
            error: "요청 시간이 초과되었습니다. 다시 시도해주세요.",
          }));
          return;
        }

        try {
          const status = await getJobStatus(jobId);
          pollErrorCount.current = 0;
          setState((prev) => ({ ...prev, progress: status.progress }));

          if (status.status === "completed" && status.recommendation_id) {
            stopPolling();
            clearJobId();
            setState({ isProcessing: false, jobId: null, progress: 0, error: null });
            window.dispatchEvent(
              new CustomEvent("recipe-ready", { detail: { id: status.recommendation_id } })
            );
            router.push(`/r/${status.recommendation_id}`);
          } else if (status.status === "failed") {
            stopPolling();
            clearJobId();
            setState((prev) => ({
              ...prev,
              isProcessing: false,
              error: status.error || "레시피 생성에 실패했습니다.",
            }));
          }
        } catch {
          // 일시적 네트워크 오류는 3회까지 재시도
          pollErrorCount.current++;
          if (pollErrorCount.current >= 3) {
            stopPolling();
            clearJobId();
            setState((prev) => ({
              ...prev,
              isProcessing: false,
              error: "작업 상태를 확인할 수 없습니다.",
            }));
          }
        }
      }, 2000);
    },
    [stopPolling, router]
  );

  const startJob = useCallback(
    (jobId: string) => {
      stopPolling();
      saveJobId(jobId);
      setState({ isProcessing: true, jobId, progress: 0, error: null });
      poll(jobId);
    },
    [stopPolling, poll]
  );

  const clearJob = useCallback(() => {
    stopPolling();
    clearJobId();
    setState({ isProcessing: false, jobId: null, progress: 0, error: null });
  }, [stopPolling]);

  // 마운트 시 저장된 작업 복원
  useEffect(() => {
    const savedJobId = loadJobId();
    if (savedJobId) {
      setState({ isProcessing: true, jobId: savedJobId, progress: 0, error: null });
      poll(savedJobId);
    }
    return () => stopPolling();
  }, [poll, stopPolling]);

  return (
    <RecipeJobContext.Provider value={{ ...state, startJob, clearJob }}>
      {children}
    </RecipeJobContext.Provider>
  );
}

export function useRecipeJob() {
  const ctx = useContext(RecipeJobContext);
  if (!ctx) throw new Error("useRecipeJob must be used within RecipeJobProvider");
  return ctx;
}
