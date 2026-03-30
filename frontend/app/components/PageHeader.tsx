import type { ReactNode } from "react";

import { cx } from "@/app/components/Card";

export default function PageHeader({
  children,
  className,
  description,
  eyebrow,
  title,
}: {
  children?: ReactNode;
  className?: string;
  description: string;
  eyebrow?: string;
  title: string;
}) {
  return (
    <header
      className={cx(
        "relative overflow-hidden rounded-[32px] border border-[var(--border-default)] bg-[linear-gradient(135deg,rgba(34,30,23,0.94),rgba(15,13,10,0.98))] p-6 shadow-[0_24px_60px_rgba(0,0,0,0.32)] before:pointer-events-none before:absolute before:right-0 before:top-0 before:h-44 before:w-44 before:bg-[radial-gradient(circle,rgba(212,168,67,0.2),transparent_58%)]",
        className
      )}
    >
      <div className="relative z-10 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-3xl">
          {eyebrow ? (
            <span className="inline-flex rounded-full bg-[rgba(212,168,67,0.12)] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-[var(--gold-400)] ring-1 ring-inset ring-[rgba(212,168,67,0.18)]">
              {eyebrow}
            </span>
          ) : null}
          <div className="mt-4 flex items-start gap-4">
            <span className="mt-1 h-14 w-px shrink-0 bg-[linear-gradient(180deg,var(--gold-400),transparent)]" />
            <div>
              <h1 className="text-3xl font-bold tracking-[-0.04em] text-[var(--text-primary)] sm:text-[2.25rem]">
                {title}
              </h1>
              <p className="mt-3 max-w-2xl text-sm leading-7 text-[var(--text-secondary)]">{description}</p>
            </div>
          </div>
        </div>
        {children ? <div className="relative z-10 flex flex-wrap gap-3">{children}</div> : null}
      </div>
    </header>
  );
}
