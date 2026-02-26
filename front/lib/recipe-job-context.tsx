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

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const poll = useCallback(
    (jobId: string) => {
      startTimeRef.current = Date.now();

      intervalRef.current = setInterval(async () => {
        // 타임아웃 체크
        if (Date.now() - startTimeRef.current > TIMEOUT_MS) {
          stopPolling();
          sessionStorage.removeItem("active-job-id");
          setState((prev) => ({
            ...prev,
            isProcessing: false,
            error: "요청 시간이 초과되었습니다. 다시 시도해주세요.",
          }));
          return;
        }

        try {
          const status = await getJobStatus(jobId);
          setState((prev) => ({ ...prev, progress: status.progress }));

          if (status.status === "completed" && status.recommendation_id) {
            stopPolling();
            sessionStorage.removeItem("active-job-id");
            setState({ isProcessing: false, jobId: null, progress: 0, error: null });
            window.dispatchEvent(
              new CustomEvent("recipe-ready", { detail: { id: status.recommendation_id } })
            );
            router.push(`/r/${status.recommendation_id}`);
          } else if (status.status === "failed") {
            stopPolling();
            sessionStorage.removeItem("active-job-id");
            setState((prev) => ({
              ...prev,
              isProcessing: false,
              error: status.error || "레시피 생성에 실패했습니다.",
            }));
          }
        } catch {
          stopPolling();
          sessionStorage.removeItem("active-job-id");
          setState((prev) => ({
            ...prev,
            isProcessing: false,
            error: "작업 상태를 확인할 수 없습니다.",
          }));
        }
      }, 2000);
    },
    [stopPolling, router]
  );

  const startJob = useCallback(
    (jobId: string) => {
      stopPolling();
      sessionStorage.setItem("active-job-id", jobId);
      setState({ isProcessing: true, jobId, progress: 0, error: null });
      poll(jobId);
    },
    [stopPolling, poll]
  );

  const clearJob = useCallback(() => {
    stopPolling();
    sessionStorage.removeItem("active-job-id");
    setState({ isProcessing: false, jobId: null, progress: 0, error: null });
  }, [stopPolling]);

  // 마운트 시 sessionStorage에서 진행 중인 작업 복원
  useEffect(() => {
    const savedJobId = sessionStorage.getItem("active-job-id");
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
