import { cn } from "@/lib/utils";

interface NuminaCardProps extends React.HTMLAttributes<HTMLDivElement> {}

export function NuminaCard({ className, children, ...props }: NuminaCardProps) {
  return (
    <div
      className={cn(
        "rounded-xl bg-card p-6 transition-all duration-300",
        "hover:-translate-y-0.5",
        className,
      )}
      style={{ boxShadow: "var(--neu-raised)" }}
      {...props}
    >
      {children}
    </div>
  );
}
