"use client";

import { cn } from "@/lib/utils";

interface BluePhoneButtonProps {
  onPress?: () => void;
  busy?: boolean;
  size?: "default" | "lg";
  label?: string;
}

export function BluePhoneButton({
  onPress,
  busy,
  size = "default",
  label = "Answer with AI memory",
}: BluePhoneButtonProps) {
  const dim = size === "lg" ? "w-24 h-24" : "w-16 h-16";
  return (
    <button
      type="button"
      onClick={onPress}
      disabled={busy}
      aria-label={label}
      className={cn(
        "rounded-full grid place-items-center text-white font-medium",
        "bg-afterglow-600 hover:bg-afterglow-700 transition-colors",
        "blue-glow animate-pulse-soft",
        "disabled:opacity-60 disabled:cursor-not-allowed",
        dim,
      )}
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="currentColor"
        className={size === "lg" ? "w-10 h-10" : "w-7 h-7"}
      >
        <path d="M22 16.92v3.08a2 2 0 0 1-2.18 2 19.91 19.91 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6A19.91 19.91 0 0 1 2.12 4.18 2 2 0 0 1 4.11 2h3.08a2 2 0 0 1 2 1.72c.13.98.37 1.94.72 2.85a2 2 0 0 1-.45 2.11L8.09 10.09a16 16 0 0 0 6 6l1.41-1.41a2 2 0 0 1 2.11-.45c.91.35 1.87.59 2.85.72A2 2 0 0 1 22 16.92Z" />
      </svg>
    </button>
  );
}
