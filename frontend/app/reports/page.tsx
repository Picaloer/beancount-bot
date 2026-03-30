"use client";

import Link from "next/link";
import useSWR from "swr";

import { cx } from "@/app/components/Card";
import EmptyState from "@/app/components/EmptyState";
import PageHeader from "@/app/components/PageHeader";
import { listMonths } from "@/lib/api";

const primaryButtonClassName =
  "inline-flex items-center justify-center rounded-xl bg-[var(--gold-400)] px-4 py-2.5 text-sm font-medium text-black transition hover:bg-[var(--gold-500)]";

export default function ReportsIndex() {
  const { data, isLoading } = useSWR("months", listMonths);
  const months = data?.months ?? [];
  const latestMonth = months[0] ?? null;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Reports Archive"
        title="财务报告"
        description="按月翻阅收入、支出、趋势和洞察。每一张报告卡都像账册目录中的一页，最新月份会被重点点亮。"
      >
        {latestMonth ? (
          <Link href={`/reports/${latestMonth}`} className={primaryButtonClassName}>
            打开最新报告
          </Link>
        ) : null}
      </PageHeader>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <div key={index} className="h-52 animate-pulse rounded-[28px] bg-[rgba(255,255,255,0.04)]" />
          ))}
        </div>
      ) : months.length === 0 ? (
        <EmptyState
          title="还没有月度报告"
          description="先导入账单，系统会按账期生成报告目录，并在详情页展示趋势图、商家排行和 AI 洞察。"
          action={
            <Link href="/import" className={primaryButtonClassName}>
              去导入账单
            </Link>
          }
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {months.map((yearMonth, index) => {
            const isLatest = index === 0;

            return (
              <Link
                key={yearMonth}
                href={`/reports/${yearMonth}`}
                className={cx(
                  "group relative overflow-hidden rounded-[30px] border p-5 transition-all hover:-translate-y-1",
                  isLatest
                    ? "border-[rgba(212,168,67,0.24)] bg-[linear-gradient(145deg,rgba(34,30,23,0.98),rgba(26,22,16,0.96))] shadow-[0_26px_60px_rgba(0,0,0,0.36)]"
                    : "border-[var(--border-default)] bg-[var(--bg-surface)] shadow-[0_20px_50px_rgba(0,0,0,0.24)]"
                )}
              >
                <div className="pointer-events-none absolute right-0 top-0 h-36 w-36 bg-[radial-gradient(circle,rgba(212,168,67,0.18),transparent_60%)] opacity-80" />
                <div className="relative z-10 flex h-full flex-col justify-between gap-8">
                  <div>
                    <div className="flex items-center justify-between gap-3">
                      <span
                        className={cx(
                          "rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em]",
                          isLatest
                            ? "bg-[rgba(212,168,67,0.14)] text-[var(--gold-400)] ring-1 ring-inset ring-[rgba(212,168,67,0.18)]"
                            : "bg-white/5 text-[var(--text-muted)]"
                        )}
                      >
                        {isLatest ? "当前月度" : "月度归档"}
                      </span>
                      <span className="text-sm text-[var(--gold-400)] transition group-hover:translate-x-0.5">进入</span>
                    </div>
                    <h2 className="mt-5 text-3xl font-bold tracking-[-0.04em] text-[var(--text-primary)]">
                      {formatYearMonth(yearMonth)}
                    </h2>
                    <p className="mt-3 text-sm leading-7 text-[var(--text-secondary)]">
                      查看收入支出概览、分类趋势、周度波动与商家排行。
                    </p>
                  </div>
                  <div className="flex items-center justify-between border-t border-white/6 pt-4 text-sm text-[var(--text-muted)]">
                    <span>{yearMonth}</span>
                    <span className="text-[var(--gold-400)]">Dark Ledger Page</span>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

function formatYearMonth(value: string) {
  const [year, month] = value.split("-");
  return `${year}年${month}月`;
}
