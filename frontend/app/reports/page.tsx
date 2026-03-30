"use client";

import Link from "next/link";
import useSWR from "swr";
import { listMonths } from "@/lib/api";

export default function ReportsIndex() {
  const { data, isLoading } = useSWR("months", listMonths);
  const months = data?.months ?? [];
  const latestMonth = months[0] ?? null;

  return (
    <div className="space-y-8">
      <section className="rounded-[32px] border border-stone-200 bg-[linear-gradient(145deg,rgba(255,251,245,0.96),rgba(244,236,223,0.92))] p-6 shadow-[0_20px_50px_rgba(97,72,38,0.09)]">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-3">
            <span className="inline-flex rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-amber-800">
              Reports Archive
            </span>
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-stone-900">财务报告</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-stone-600">
                按月回看收入、支出与消费结构变化。除了单月快照，也可以进入详情页查看近 6 个月的分类趋势，识别持续升温的开销。
              </p>
            </div>
          </div>

          {latestMonth && (
            <Link
              href={`/reports/${latestMonth}`}
              className="inline-flex items-center justify-center rounded-xl bg-amber-700 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-amber-800"
            >
              打开最新报告
            </Link>
          )}
        </div>
      </section>

      {isLoading ? (
        <div className="py-24 text-center text-stone-400">正在整理账期列表...</div>
      ) : months.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-stone-200 bg-white/80 px-6 py-20 text-center text-stone-400 shadow-[0_18px_40px_rgba(84,62,34,0.05)]">
          <p className="mb-3 text-4xl">帐</p>
          <p>
            还没有可查看的报告，请先
            <Link href="/import" className="text-amber-700 hover:underline">
              导入账单
            </Link>
          </p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {months.map((yearMonth, index) => (
            <Link
              key={yearMonth}
              href={`/reports/${yearMonth}`}
              className="group rounded-3xl border border-stone-200 bg-white/90 p-5 shadow-[0_18px_40px_rgba(84,62,34,0.06)] transition-all hover:-translate-y-0.5 hover:border-amber-300 hover:shadow-[0_22px_44px_rgba(84,62,34,0.1)]"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.18em] text-stone-400">
                    {index === 0 ? "最新账期" : "月度归档"}
                  </p>
                  <h2 className="mt-3 text-2xl font-bold text-stone-900">{formatYearMonth(yearMonth)}</h2>
                  <p className="mt-2 text-sm text-stone-500">查看收入支出概览、分类趋势、商家排行与 AI 洞察</p>
                </div>
                <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800 transition-colors group-hover:bg-amber-200">
                  打开
                </span>
              </div>
              <div className="mt-6 flex items-center justify-between border-t border-stone-100 pt-4 text-sm text-stone-500">
                <span>{yearMonth}</span>
                <span className="text-amber-700 transition-transform group-hover:translate-x-0.5">进入报告</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function formatYearMonth(value: string) {
  const [year, month] = value.split("-");
  return `${year}年${month}月`;
}
