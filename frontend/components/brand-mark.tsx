export function BrandMark({ size = 34 }: { size?: number }) {
  return (
    <svg aria-hidden="true" className="brand-mark" height={size} viewBox="0 0 40 40" width={size}>
      <path d="M20 2 35 10v12c0 8-6.2 13.2-15 16C11.2 35.2 5 30 5 22V10L20 2Z" />
      <circle cx="18" cy="19" r="7" />
      <path d="m23 24 6 6M15 19h6M18 16v6" />
    </svg>
  );
}
