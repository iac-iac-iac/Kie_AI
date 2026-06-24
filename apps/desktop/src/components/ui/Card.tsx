import { cn } from "../../lib/utils";

export function Card({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={cn("glass-panel rounded-2xl p-6", className)}>{children}</div>
  );
}

export function CardTitle({ children }: { children: React.ReactNode }) {
  return <h2 className="text-primary mb-4 text-lg font-semibold">{children}</h2>;
}
