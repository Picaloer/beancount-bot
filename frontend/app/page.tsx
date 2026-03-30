"use client";

import Link from "next/link";
import useSWR from "swr";

import { SourceBadge, StatusBadge } from "@/app/components/Badge";
import Card, { cardClassName, cx } from "@/app/components/Card";
import EmptyState from "@/app/components/EmptyState";
import PageHeader from "@/app/components/PageHeader";
import ProgressBar from "@/app/components/ProgressBar";
import StatCard from "@/app/components/StatCard";
import { getBudgetPlan, getTransactionSummary, listImports, listMonths } from "@/lib/api";

const currencyFormatter = new Intl.NumberFormat("zh-CN", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const primaryLinkClassName =
  "inline-flex items-center justify-center rounded-xl bg-[var(--gold-400)] px-4 py-2.5 text-sm font-medium text-black transition hover:bg-[var(--gold-500)]";

const secondaryLinkClassName =
  "inline-flex items-center justify-center rounded-xl border border-[rgba(212,168,67,0.28)] bg-[rgba(255,255,255,0.02)] px-4 py-2.5 text-sm font-medium text-[var(--gold-400)] transition hover:bg-[rgba(212,168,67,0.08)] hover:text-[var(--text-primary)]";

export default function Dashboard() {
  const { data: summary } = useSWR("summary", getTransactionSummary);
  const { data: imports } = useSWR("imports", listImports);
  const { data: months } = useSWR("months", listMonths);

  const latestMonth = months?.months?.[0];
  const { data: budget } = useSWR(
    latestMonth ? ["budget", latestMonth] : null,
    ([, yearMonth]) => getBudgetPlan(yearMonth)
  );

  const totalExpense = summary?.expense?.total ?? 0;
  const totalIncome = summary?.income?.total ?? 0;
  const net = totalIncome - totalExpense;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Dark Ledger Overview"
        title="财务看板"
        description="把导入、预算、报告和分类结果集中在一册暗金账本里。先看累计收支，再决定本月该补哪一页。"
      >
        <Link href="/import" className={primaryLinkClassName}>
          立即导入账单
        </Link>
        <Link href={latestMonth ? `/reports/${latestMonth}` : "/reports"} className={secondaryLinkClassName}>
          {latestMonth ? `查看 ${latestMonth} 报告` : "浏览财务报告"}
        </Link>
      </PageHeader>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard
          label="累计支出"
          tone="rose"
          value={formatCurrency(totalExpense)}
          hint={`${summary?.expense?.count ?? 0} 笔支出`}
        />
        <StatCard
          label="累计收入"
          tone="emerald"
          value={formatCurrency(totalIncome)}
          hint={`${summary?.income?.count ?? 0} 笔收入`}
        />
        <StatCard
          label="净资产变化"
          tone={net >= 0 ? "gold" : "rose"}
          value={`${net >= 0 ? "+" : ""}${formatCurrency(net)}`}
          hint={net >= 0 ? "账面净流入" : "账面净流出"}
        />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.55fr_1fr]">
        <Card variant="surface" className="p-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Budget Ledger</p>
              <h2 className="mt-3 text-2xl font-bold tracking-[-0.03em] text-[var(--text-primary)]">
                {latestMonth ? `${latestMonth} 月预算总览` : "等待首个账期"}
              </h2>
              <p className="mt-2 max-w-2xl text-sm leading-7 text-[var(--text-secondary)]">
                {latestMonth
                  ? "从自动预算建议里先看整体使用率，再确认哪些分类已经逼近上限。"
                  : "导入账单后，这里会生成预算总额、分类建议和整体执行率。"}
              </p>
            </div>
            <Link
              href={latestMonth ? `/budgets/${latestMonth}` : "/budgets"}
              className="inline-flex items-center rounded-xl border border-[rgba(212,168,67,0.22)] px-4 py-2 text-sm font-medium text-[var(--gold-400)] transition hover:bg-[rgba(212,168,67,0.08)]"
            >
              查看预算详情
            </Link>
          </div>

          {!latestMonth ? (
            <div className="mt-6">
              <EmptyState
                title="还没有预算页"
                description="先导入微信、支付宝或招商银行账单，系统会按历史消费趋势生成预算建议。"
                action={
                  <Link href="/import" className={primaryLinkClassName}>
                    去导入账单
                  </Link>
                }
              />
            </div>
          ) : !budget ? (
            <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
              <SkeletonPanel />
              <SkeletonPanel />
              <SkeletonPanel />
            </div>
          ) : (
            <>
              <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
                <BudgetMetric title="预算总额" value={budget.total_budget} accent="text-[var(--gold-400)]" />
                <BudgetMetric title="已支出" value={budget.total_spent} accent="text-rose-300" />
                <BudgetMetric
                  title="剩余空间"
                  value={budget.remaining}
                  accent={budget.remaining >= 0 ? "text-emerald-300" : "text-rose-300"}
                />
              </div>

              <div className="mt-6 rounded-[24px] border border-[var(--border-subtle)] bg-[rgba(255,255,255,0.02)] p-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm text-[var(--text-secondary)]">整体使用率</p>
                    <p className="mt-1 text-xs text-[var(--text-muted)]">
                      {budget.generated ? "已按最新流水重新生成预算建议" : "当前展示缓存预算"}
                    </p>
                  </div>
                  <span className="tabular rounded-full bg-white/5 px-3 py-1 text-sm text-[var(--text-primary)]">
                    {budget.usage_percentage.toFixed(1)}%
                  </span>
                </div>
                <ProgressBar
                  className="mt-4"
                  tone={budgetTone(budget.usage_percentage)}
                  value={budget.usage_percentage}
                  valueLabel={`${budget.usage_percentage.toFixed(1)}%`}
                />
              </div>

              <div className="mt-6 grid grid-cols-1 gap-3 xl:grid-cols-2">
                {budget.categories.slice(0, 4).map((category) => (
                  <div
                    key={category.id}
                    className="rounded-[22px] border border-[var(--border-subtle)] bg-[rgba(255,255,255,0.02)] p-4"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-medium text-[var(--text-primary)]">{category.category_l1}</p>
                        <p className="mt-1 text-sm text-[var(--text-muted)]">
                          已支出 {formatCurrency(category.spent)} / 预算 {formatCurrency(category.budget)}
                        </p>
                      </div>
                      <span className={budgetStatusClassName(category.status)}>{budgetStatusLabel(category.status)}</span>
                    </div>
                    <ProgressBar
                      className="mt-4"
                      size="sm"
                      tone={budgetStatusTone(category.status)}
                      value={category.usage_percentage}
                      valueLabel={`${category.usage_percentage.toFixed(1)}%`}
                    />
                  </div>
                ))}
              </div>
            </>
          )}
        </Card>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-1">
          <QuickActionCard
            href="/import"
            icon={<UploadIcon className="h-6 w-6" />}
            title="导入账单"
            description="上传微信、支付宝或招商银行账单，开启新的分类批次。"
          />
          <QuickActionCard
            href={latestMonth ? `/reports/${latestMonth}` : "/transactions"}
            icon={<InsightIcon className="h-6 w-6" />}
            title={latestMonth ? `${latestMonth} 月报告` : "查看交易明细"}
            description={
              latestMonth
                ? "进入最新账期，查看图表、商家排行和 AI 财务洞察。"
                : "当前还没有月报，先去查看已导入的交易流水。"
            }
          />
        </div>
      </div>

      <section className="space-y-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold tracking-[-0.02em] text-[var(--text-primary)]">最近导入</h2>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">最近几次账单导入状态，适合快速确认分类流水是否已经落库。</p>
          </div>
          <Link href="/import" className="text-sm font-medium text-[var(--gold-400)] transition hover:text-[var(--text-primary)]">
            查看全部
          </Link>
        </div>

        {!imports || imports.length === 0 ? (
          <EmptyState
            title="还没有导入记录"
            description="导入一份账单后，这里会按卡片时间线展示文件来源、状态和交易条数。"
            action={
              <Link href="/import" className={primaryLinkClassName}>
                去导入账单
              </Link>
            }
          />
        ) : (
          <div className="grid gap-3">
            {imports.slice(0, 5).map((record) => (
              <Card key={record.import_id} variant="surface" className="p-5">
                <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="max-w-full truncate text-base font-semibold text-[var(--text-primary)]">
                        {record.file_name}
                      </p>
                      <SourceBadge source={record.source} />
                      <StatusBadge status={record.status} />
                    </div>
                    <p className="mt-3 text-sm text-[var(--text-secondary)]">
                      {formatImportTime(record.imported_at)}
                      <span className="mx-2 text-[var(--text-muted)]">/</span>
                      <span className="tabular">{record.row_count} 条交易</span>
                    </p>
                    {record.error_message && record.status === "failed" ? (
                      <p className="mt-2 text-sm text-rose-300">{record.error_message}</p>
                    ) : null}
                  </div>
                  <div className="flex items-center gap-3">
                    {record.status === "done" ? (
                      <Link href="/transactions" className={secondaryLinkClassName}>
                        查看交易
                      </Link>
                    ) : (
                      <span className="rounded-full bg-white/5 px-3 py-1 text-xs text-[var(--text-muted)]">
                        处理中会自动刷新
                      </span>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function BudgetMetric({
  accent,
  title,
  value,
}: {
  accent: string;
  title: string;
  value: number;
}) {
  return (
    <div className="rounded-[22px] border border-[var(--border-subtle)] bg-[rgba(255,255,255,0.03)] p-4">
      <p className="text-sm text-[var(--text-secondary)]">{title}</p>
      <p className={cx("tabular mt-2 text-2xl font-bold tracking-[-0.03em]", accent)}>{formatCurrency(value)}</p>
    </div>
  );
}

function QuickActionCard({
  description,
  href,
  icon,
  title,
}: {
  description: string;
  href: string;
  icon: React.ReactNode;
  title: string;
}) {
  return (
    <Link
      href={href}
      className={cardClassName(
        "surface",
        "group block p-5 transition hover:-translate-y-0.5 hover:border-[rgba(212,168,67,0.28)]"
      )}
    >
      <div className="flex items-start gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[rgba(212,168,67,0.12)] text-[var(--gold-400)]">
          {icon}
        </div>
        <div>
          <p className="text-base font-semibold text-[var(--text-primary)]">{title}</p>
          <p className="mt-2 text-sm leading-7 text-[var(--text-secondary)]">{description}</p>
          <p className="mt-4 text-sm font-medium text-[var(--gold-400)] transition group-hover:text-[var(--text-primary)]">
            打开页面
          </p>
        </div>
      </div>
    </Link>
  );
}

function SkeletonPanel() {
  return <div className="h-28 animate-pulse rounded-[22px] bg-[rgba(255,255,255,0.04)]" />;
}

function UploadIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
      <path d="M12 5V14" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M8 10.5L12 14.5L16 10.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M5 18.5H19" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function InsightIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
      <path d="M5 18.5V11" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M12 18.5V6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M19 18.5V13.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function formatCurrency(value: number) {
  return `¥${currencyFormatter.format(value)}`;
}

function budgetTone(usage: number) {
  if (usage >= 100) {
    return "overspent" as const;
  }
  if (usage >= 80) {
    return "warning" as const;
  }
  return "gold" as const;
}

function budgetStatusTone(status: "healthy" | "warning" | "overspent") {
  if (status === "overspent") {
    return "overspent" as const;
  }
  if (status === "warning") {
    return "warning" as const;
  }
  return "healthy" as const;
}

function budgetStatusClassName(status: "healthy" | "warning" | "overspent") {
  if (status === "overspent") {
    return "rounded-full bg-rose-400/10 px-3 py-1 text-xs font-medium text-rose-300 ring-1 ring-inset ring-rose-400/20";
  }
  if (status === "warning") {
    return "rounded-full bg-amber-400/10 px-3 py-1 text-xs font-medium text-amber-300 ring-1 ring-inset ring-amber-400/20";
  }
  return "rounded-full bg-emerald-400/10 px-3 py-1 text-xs font-medium text-emerald-300 ring-1 ring-inset ring-emerald-400/20";
}

function budgetStatusLabel(status: "healthy" | "warning" | "overspent") {
  if (status === "overspent") {
    return "超支";
  }
  if (status === "warning") {
    return "预警";
  }
  return "健康";
}

function formatImportTime(value: string) {
  return new Date(value).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Shanghai",
  });
}
