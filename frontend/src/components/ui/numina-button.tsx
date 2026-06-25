import { cn } from "@/lib/utils";

const buttonVariantsBase =
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-medium text-white transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 active:scale-[0.97]";

export interface NuminaButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "destructive";
}

export function NuminaButton({
  className,
  variant = "primary",
  children,
  ...props
}: NuminaButtonProps) {
  const variantStyles = {
    primary: "bg-[#4f46e5] hover:brightness-110",
    destructive: "bg-[#ef4444] hover:brightness-110",
  };

  return (
    <button
      className={cn(
        buttonVariantsBase,
        variantStyles[variant],
        "tech-btn-shimmer",
        className,
      )}
      style={{
        boxShadow:
          "6px 6px 12px var(--neu-shadow-dark), -6px -6px 12px var(--neu-shadow-light)",
      }}
      {...props}
    >
      {children}
    </button>
  );
}
