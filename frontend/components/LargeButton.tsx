export default function LargeButton({ children, className = "", ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button className={`focus-ring min-h-[52px] rounded-md px-5 py-3 text-lg font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${className}`} {...props}>{children}</button>;
}
