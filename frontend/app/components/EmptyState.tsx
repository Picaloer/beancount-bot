import type { ReactNode } from "react";

import Card, { cx } from "@/app/components/Card";

export default function EmptyState({
  action,
  className,
  description,
  title,
}: {
  action?: ReactNode;
  className?: string;
  description: string;
  title: string;
}) {
  return (
    <Card variant="bordered" className={cx("p-10 text-center sm:p-14", className)}>
      <div className="mx-auto flex max-w-md flex-col items-center">
        <LedgerMark />
        <h2 className="mt-6 text-xl font-bold tracking-[-0.02em] text-[var(--text-primary)]">{title}</h2>
        <p className="mt-3 text-sm leading-7 text-[var(--text-secondary)]">{description}</p>
        {action ? <div className="mt-6 flex flex-wrap justify-center gap-3">{action}</div> : null}
      </div>
    </Card>
  );
}

function LedgerMark() {
  return (
    <svg
      aria-hidden="true"
      className="h-28 w-28 text-[var(--gold-400)]"
      viewBox="0 0 120 120"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect x="20" y="16" width="80" height="92" rx="18" fill="rgba(212,168,67,0.08)" stroke="currentColor" strokeOpacity="0.35" />
      <path d="M36 38H84" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
      <path d="M36 54H72" stroke="currentColor" strokeWidth="3" strokeOpacity="0.7" strokeLinecap="round" />
      <path d="M36 70H78" stroke="currentColor" strokeWidth="3" strokeOpacity="0.55" strokeLinecap="round" />
      <path d="M36 86H66" stroke="currentColor" strokeWidth="3" strokeOpacity="0.4" strokeLinecap="round" />
      <circle cx="84" cy="82" r="12" fill="rgba(212,168,67,0.12)" stroke="currentColor" strokeWidth="2.5" />
      <path d="M84 76V88" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M78 82H90" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M60 8V22" stroke="currentColor" strokeOpacity="0.65" strokeWidth="2" strokeLinecap="round" />
      <path d="M108 60H94" stroke="currentColor" strokeOpacity="0.55" strokeWidth="2" strokeLinecap="round" />
      <path d="M12 60H26" stroke="currentColor" strokeOpacity="0.55" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}
