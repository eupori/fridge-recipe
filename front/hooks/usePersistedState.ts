import { useState, useEffect, useCallback, Dispatch, SetStateAction } from "react";

export function usePersistedState<T>(
  key: string,
  defaultValue: T
): [T, Dispatch<SetStateAction<T>>] {
  const [value, setValue] = useState<T>(defaultValue);
  const [isHydrated, setIsHydrated] = useState(false);

  // 클라이언트 사이드에서 localStorage 값 로드
  useEffect(() => {
    try {
      const stored = localStorage.getItem(key);
      if (stored !== null) {
        setValue(JSON.parse(stored));
      }
    } catch {
      // localStorage 접근 실패 또는 JSON 파싱 실패 시 기본값 유지
    }
    setIsHydrated(true);
  }, [key]);

  // 값이 변경되면 localStorage에 저장
  useEffect(() => {
    if (isHydrated) {
      try {
        localStorage.setItem(key, JSON.stringify(value));
      } catch {
        // localStorage 저장 실패 시 무시 (quota 초과 등)
      }
    }
  }, [key, value, isHydrated]);

  return [value, setValue];
}
