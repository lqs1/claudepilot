import { cn } from "@/lib/utils";

interface NuminaInputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {}

export function NuminaInput({ className, ...props }: NuminaInputProps) {
  return (
    <input
      className={cn(
        "numina-input h-10 w-full rounded-xl border-0 bg-card px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      style={{ boxShadow: "var(--neu-pressed-sm)" }}
      {...props}
    />
  );
}
