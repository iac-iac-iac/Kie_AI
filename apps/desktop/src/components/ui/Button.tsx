import { ButtonHTMLAttributes, forwardRef } from "react";
import { cn } from "../../lib/utils";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "ghost" | "outline";
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-medium transition-all disabled:opacity-50",
        variant === "default" && "bg-accent text-white shadow-lg hover:bg-[var(--accent-hover)]",
        variant === "ghost" && "text-primary hover:bg-[var(--hover-bg)]",
        variant === "outline" && "border border-[var(--input-border)] bg-[var(--input-bg)] text-primary hover:bg-[var(--hover-bg)]",
        className,
      )}
      {...props}
    />
  ),
);
Button.displayName = "Button";
