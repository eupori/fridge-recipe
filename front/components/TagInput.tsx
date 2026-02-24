"use client";

import { useState, useRef, useCallback, KeyboardEvent } from "react";
import { Badge } from "@/components/ui/badge";
import { X, Plus } from "lucide-react";

interface TagInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  id?: string;
}

export function TagInput({ value, onChange, placeholder, disabled, id }: TagInputProps) {
  const [inputValue, setInputValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const tags = value
    .split(/,|\n/)
    .map((s) => s.trim())
    .filter(Boolean);

  const updateTags = useCallback(
    (newTags: string[]) => {
      onChange(newTags.join(", "));
    },
    [onChange]
  );

  const addTag = useCallback(
    (raw: string) => {
      const tag = raw.trim();
      if (!tag) return;
      if (tags.includes(tag)) {
        setInputValue("");
        return;
      }
      updateTags([...tags, tag]);
      setInputValue("");
    },
    [tags, updateTags]
  );

  const removeTag = useCallback(
    (index: number) => {
      updateTags(tags.filter((_, i) => i !== index));
    },
    [tags, updateTags]
  );

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    // 한글 IME 조합 중에는 키 이벤트 무시 (조합 완료 전 addTag 방지)
    if (e.nativeEvent.isComposing) return;
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addTag(inputValue);
    } else if (e.key === "Backspace" && inputValue === "" && tags.length > 0) {
      removeTag(tags.length - 1);
    }
  };

  const handleInputChange = (val: string) => {
    // comma typed → add tag immediately
    if (val.includes(",")) {
      const parts = val.split(",");
      for (const part of parts.slice(0, -1)) {
        addTag(part);
      }
      setInputValue(parts[parts.length - 1]);
      return;
    }
    setInputValue(val);
  };

  return (
    <div
      ref={containerRef}
      className={`flex flex-wrap items-start gap-1.5 p-2 min-h-[80px] border border-input rounded-md bg-background cursor-text transition-shadow focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2 ${
        disabled ? "opacity-50 cursor-not-allowed" : ""
      }`}
      onClick={() => !disabled && inputRef.current?.focus()}
    >
      {tags.map((tag, i) => (
        <Badge key={`${tag}-${i}`} variant="secondary" className="gap-1 pr-1 text-sm">
          {tag}
          {!disabled && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                removeTag(i);
              }}
              className="ml-0.5 rounded-full hover:bg-secondary-foreground/20 p-0.5"
              aria-label={`${tag} 삭제`}
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </Badge>
      ))}
      <div className="flex items-center gap-1 flex-1 min-w-[80px]">
        <input
          ref={inputRef}
          id={id}
          type="text"
          value={inputValue}
          onChange={(e) => handleInputChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={() => addTag(inputValue)}
          placeholder={tags.length === 0 ? placeholder : "재료 추가..."}
          disabled={disabled}
          className="flex-1 bg-transparent outline-none text-sm py-1 min-w-0 placeholder:text-muted-foreground"
        />
        {inputValue.trim() && !disabled && (
          <button
            type="button"
            onClick={() => addTag(inputValue)}
            className="shrink-0 p-1 rounded-md hover:bg-muted transition-colors"
            aria-label="재료 추가"
          >
            <Plus className="w-4 h-4 text-muted-foreground" />
          </button>
        )}
      </div>
    </div>
  );
}
