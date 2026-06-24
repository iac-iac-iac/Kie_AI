import { cn } from "../../lib/utils";

export function Slider({
  value,
  min,
  max,
  step,
  onChange,
  showValue = true,
  className,
}: {
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (value: number) => void;
  showValue?: boolean;
  className?: string;
}) {
  return (
    <div className={cn("flex items-center gap-3", className)}>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="h-2 flex-1 cursor-pointer accent-accent"
      />
      {showValue && (
        <span className="w-10 shrink-0 text-right text-sm tabular-nums text-subtle">
          {value}
        </span>
      )}
    </div>
  );
}
