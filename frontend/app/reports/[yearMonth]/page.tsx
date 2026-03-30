"use client";

import { use } from "react";
import Link from "next/link";
import useSWR from "swr";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import Card from "@/app/components/Card";
import EmptyState from "@/app/components/EmptyState";
import PageHeader from "@/app/components/PageHeader";
import ProgressBar from "@/app/components/ProgressBar";
import StatCard from "@/app/components/StatCard";
import { getCategoryTrends, getMerchantRanking, getMonthlyReport } from "@/lib/api";

const CHART_COLORS = [
  "#d4a843",
  "#b8882a",
  "#34d399",
  "#f87171",
  "#38bdf8",
  "#a78bfa",
  "#fb923c",
  "#4ade80",
];

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const currencyFormatter = new Intl.NumberFormat("zh-CN", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const primaryButtonClassName =
  "inline-flex items-center justify-center rounded-xl bg-[var(--gold-400)] px-4 py-2.5 text-sm font-medium text-black transition hover:bg-[var(--gold-500)]";

const secondaryButtonClassName =
  "inline-flex items-center justify-center rounded-xl border border-[rgba(212,168,67,0.4)] px-4 py-2.5 text-sm font-medium text-[var(--gold-400)] transition hover:bg-[rgba(212,168,67,0.1)]";

export default function MonthlyReportPage({
  params,
}: {
  params: Promise<{ yearMonth: string }>;
}) {
  const { yearMonth } = use(params);
  const ym = decodeURIComponent(yearMonth);

  const { data: report, isLoading, mutate } = useSWR(["report", ym], () => getMonthlyReport(ym));
  const { data: ranking } = useSWR(["ranking", ym], () => getMerchantRanking(ym, 10));
  const { data: trends } = useSWR(["category-trends", ym], () => getCategoryTrends(ym, 6, 5));

  if (isLoading) {
    return <div className="py-24 text-center text-[var(--text-muted)]">正在整理本月账目与洞察...</div>;
  }

  if (!report) {
    return (
      <EmptyState
        title="这页报告还是空白"
        description="当前账期还没有可展示的数据，请先导入账单，系统才会生成月度报告。"
        action={
          <Link href="/import" className={primaryButtonClassName}>
            去导入账单
          </Link>
        }
      />
    );
  }

  const trendCategories = trends?.categories ?? [];
  const trendPoints = trends?.points ?? [];
  const trendWindow =
    trends && trends.months.length > 0
      ? `${formatYearMonth(trends.months[0])} - ${formatYearMonth(trends.months[trends.months.length - 1])}`
      : "最近 6 个月";

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Monthly Report"
        title={`${ym} 财务报告`}
        description="从支出结构、周度波动到商家排行，快速看清这个月的钱流向了哪里，以及过去半年里哪些分类正在持续抬升。"
      >
        <Link href="/reports" className={secondaryButtonClassName}>
          返回报告目录
        </Link>
        <a
          href={`${API_BASE}/reports/beancount/${ym}`}
          target="_blank"
          rel="noopener noreferrer"
          className={secondaryButtonClassName}
        >
          导出 Beancount
        </a>
        <button
          type="button"
          onClick={() => mutate(getMonthlyReport(ym, true))}
          className={primaryButtonClassName}
        >
          重新生成
        </button>
      </PageHeader>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="总支出" value={formatCurrency(report.total_expense)} tone="rose" hint="本月支出" />
        <StatCard label="总收入" value={formatCurrency(report.total_income)} tone="emerald" hint="本月收入" />
        <StatCard
          label="净收支"
          value={`${report.net >= 0 ? "+" : ""}${formatCurrency(report.net)}`}
          tone={report.net >= 0 ? "gold" : "rose"}
          hint={report.net >= 0 ? "正向结余" : "负向结余"}
        />
        <StatCard label="交易笔数" value={`${report.transaction_count} 笔`} tone="sky" hint={report.cached ? "缓存结果" : "实时生成"} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <Card variant="surface" className="p-5">
          <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-[var(--text-primary)]">近 6 个月分类消费趋势</h2>
              <p className="mt-1 text-sm text-[var(--text-secondary)]">观察高频支出分类的月度变化，判断哪些开销正在持续走高。</p>
            </div>
            <span className="text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">{trendWindow}</span>
          </div>

          {trendCategories.length === 0 ? (
            <EmptyState
              className="p-6"
              title="历史月份还不够"
              description="继续导入更多月份后，这里会显示近 6 个月的分类变化曲线。"
            />
          ) : (
            <>
              <div className="mb-4 flex flex-wrap gap-2">
                {trendCategories.map((category, index) => (
                  <span
                    key={category}
                    className="inline-flex items-center gap-2 rounded-full border border-white/6 bg-[var(--bg-elevated)] px-3 py-1 text-xs font-medium text-[var(--text-secondary)]"
                  >
                    <span
                      className="h-2.5 w-2.5 rounded-full"
                      style={{ backgroundColor: CHART_COLORS[index % CHART_COLORS.length] }}
                    />
                    {category}
                  </span>
                ))}
              </div>
              <ResponsiveContainer width="100%" height={320}>
                <LineChart data={trendPoints} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                  <XAxis
                    dataKey="year_month"
                    tickFormatter={formatMonthTick}
                    tick={{ fontSize: 12, fill: "#b5a898" }}
                    axisLine={{ stroke: "rgba(212,168,67,0.16)" }}
                    tickLine={{ stroke: "rgba(212,168,67,0.16)" }}
                  />
                  <YAxis
                    tickFormatter={formatAxisCurrency}
                    tick={{ fontSize: 12, fill: "#b5a898" }}
                    axisLine={{ stroke: "rgba(212,168,67,0.16)" }}
                    tickLine={{ stroke: "rgba(212,168,67,0.16)" }}
                    width={72}
                  />
                  <Tooltip
                    labelFormatter={(value) => formatYearMonth(String(value))}
                    formatter={(value, name) => [formatCurrency(Number(value ?? 0)), String(name ?? "")]}
                    contentStyle={{
                      backgroundColor: "#1a1610",
                      borderRadius: 16,
                      borderColor: "rgba(212,168,67,0.18)",
                      color: "#f5ede0",
                      boxShadow: "0 12px 30px rgba(0, 0, 0, 0.3)",
                    }}
                  />
                  {trendCategories.map((category, index) => (
                    <Line
                      key={category}
                      type="monotone"
                      dataKey={category}
                      stroke={CHART_COLORS[index % CHART_COLORS.length]}
                      strokeWidth={2.5}
                      dot={{ r: 3, strokeWidth: 0 }}
                      activeDot={{ r: 5 }}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </>
          )}
        </Card>

        <Card variant="surface" className="p-5">
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-[var(--text-primary)]">趋势焦点</h2>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">按近 6 个月累计金额选出最值得关注的分类。</p>
          </div>

          <div className="space-y-3">
            {(trends?.top_categories ?? []).length === 0 ? (
              <EmptyState className="p-6" title="暂无趋势焦点" description="继续导入更多月份后，这里会显示最值得关注的分类。" />
            ) : (
              (trends?.top_categories ?? []).map((item, index) => (
                <div key={item.category_l1} className="rounded-[22px] border border-[var(--border-subtle)] bg-[var(--bg-elevated)] p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="flex items-center gap-2 font-medium text-[var(--text-primary)]">
                        <span
                          className="h-2.5 w-2.5 rounded-full"
                          style={{ backgroundColor: CHART_COLORS[index % CHART_COLORS.length] }}
                        />
                        <span className="truncate">{item.category_l1}</span>
                      </p>
                      <p className="mt-1 text-xs uppercase tracking-[0.16em] text-[var(--text-muted)]">近 6 个月累计</p>
                    </div>
                    <span className="tabular text-sm font-semibold text-[var(--text-primary)]">{formatCurrency(item.total)}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card variant="surface" className="p-5">
          <h2 className="mb-4 text-lg font-semibold text-[var(--text-primary)]">支出分类占比</h2>
          {report.category_breakdown.length === 0 ? (
            <EmptyState className="p-6" title="暂无支出数据" description="当前账期缺少支出记录，因此还不能绘制分类占比图。" />
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={report.category_breakdown}
                  cx="50%"
                  cy="50%"
                  outerRadius={96}
                  dataKey="amount"
                  nameKey="category_l1"
                  label={false}
                  labelLine={false}
                >
                  {report.category_breakdown.map((_, index) => (
                    <Cell key={index} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value, name) => [formatCurrency(Number(value ?? 0)), String(name ?? "金额")]}
                  contentStyle={{
                    backgroundColor: "#1a1610",
                    borderRadius: 16,
                    borderColor: "rgba(212,168,67,0.18)",
                    color: "#f5ede0",
                    boxShadow: "0 12px 30px rgba(0, 0, 0, 0.3)",
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </Card>

        <Card variant="surface" className="p-5">
          <h2 className="mb-4 text-lg font-semibold text-[var(--text-primary)]">按周支出分布</h2>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={report.weekly_expense} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
              <XAxis
                dataKey="week"
                tickFormatter={(value) => `第${value}周`}
                tick={{ fontSize: 12, fill: "#b5a898" }}
                axisLine={{ stroke: "rgba(212,168,67,0.16)" }}
                tickLine={{ stroke: "rgba(212,168,67,0.16)" }}
              />
              <YAxis
                tick={{ fontSize: 12, fill: "#b5a898" }}
                tickFormatter={formatAxisCurrency}
                axisLine={{ stroke: "rgba(212,168,67,0.16)" }}
                tickLine={{ stroke: "rgba(212,168,67,0.16)" }}
                width={72}
              />
              <Tooltip
                formatter={(value, name) => [formatCurrency(Number(value ?? 0)), String(name ?? "支出")]}
                contentStyle={{
                  backgroundColor: "#1a1610",
                  borderRadius: 16,
                  borderColor: "rgba(212,168,67,0.18)",
                  color: "#f5ede0",
                  boxShadow: "0 12px 30px rgba(0, 0, 0, 0.3)",
                }}
              />
              <Bar dataKey="amount" fill="#d4a843" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      <Card variant="surface" className="overflow-hidden">
        <div className="border-b border-white/6 px-5 py-4">
          <h2 className="text-lg font-semibold text-[var(--text-primary)]">分类支出明细</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-[var(--bg-elevated)] text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">
              <tr>
                <th className="px-5 py-3 text-left">分类</th>
                <th className="px-5 py-3 text-right">金额</th>
                <th className="px-5 py-3 text-right">占比</th>
                <th className="px-5 py-3">趋势条</th>
              </tr>
            </thead>
            <tbody>
              {report.category_breakdown.map((cat, index) => (
                <tr key={cat.category_l1} className="border-t border-white/6 hover:bg-[var(--bg-elevated)]">
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2 text-[var(--text-primary)]">
                      <span
                        className="inline-block h-3 w-3 rounded-full"
                        style={{ backgroundColor: CHART_COLORS[index % CHART_COLORS.length] }}
                      />
                      <span>{cat.category_l1}</span>
                    </div>
                  </td>
                  <td className="tabular px-5 py-3 text-right font-medium text-[var(--text-primary)]">{formatCurrency(cat.amount)}</td>
                  <td className="tabular px-5 py-3 text-right text-[var(--text-secondary)]">{cat.percentage}%</td>
                  <td className="px-5 py-3">
                    <ProgressBar
                      size="sm"
                      tone="gold"
                      value={cat.percentage}
                      valueLabel={`${cat.percentage}%`}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {(ranking ?? []).length > 0 ? (
        <Card variant="surface" className="overflow-hidden">
          <div className="border-b border-white/6 px-5 py-4">
            <h2 className="text-lg font-semibold text-[var(--text-primary)]">商家支出排行榜 TOP 10</h2>
          </div>
          <div className="divide-y divide-white/6">
            {(ranking ?? []).map((merchant, index) => (
              <div key={merchant.merchant} className="flex items-center gap-4 px-5 py-3 hover:bg-[var(--bg-elevated)]">
                <span
                  className={
                    index < 3
                      ? "flex h-8 w-8 items-center justify-center rounded-full bg-[rgba(212,168,67,0.14)] text-sm font-bold text-[var(--gold-400)]"
                      : "flex h-8 w-8 items-center justify-center rounded-full bg-white/5 text-sm font-bold text-[var(--text-muted)]"
                  }
                >
                  {index + 1}
                </span>
                <span className="flex-1 truncate text-sm text-[var(--text-primary)]">{merchant.merchant}</span>
                <span className="tabular text-sm text-[var(--text-secondary)]">{merchant.count} 笔</span>
                <span className="tabular text-sm font-semibold text-[var(--text-primary)]">{formatCurrency(merchant.total)}</span>
              </div>
            ))}
          </div>
        </Card>
      ) : null}

      {report.ai_insight ? (
        <Card variant="elevated" className="border-l-4 border-l-[var(--gold-400)] p-6">
          <div className="mb-3 flex items-center gap-3">
            <div className="rounded-full bg-[rgba(212,168,67,0.1)] px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--gold-400)] ring-1 ring-inset ring-[rgba(212,168,67,0.2)]">
              AI 洞察
            </div>
            <h2 className="text-lg font-semibold text-[var(--text-primary)]">本月财务洞察</h2>
          </div>
          <p className="text-sm leading-8 text-[var(--text-secondary)]">{report.ai_insight}</p>
        </Card>
      ) : null}
    </div>
  );
}

function formatCurrency(value: number) {
  return `¥${currencyFormatter.format(value)}`;
}

function formatAxisCurrency(value: number | string) {
  const amount = Number(value);
  if (Math.abs(amount) >= 10000) {
    return `¥${(amount / 10000).toFixed(1)}w`;
  }
  return `¥${Math.round(amount)}`;
}

function formatMonthTick(value: string) {
  return `${value.slice(5)}月`;
}

function formatYearMonth(value: string) {
  const [year, month] = value.split("-");
  return `${year}年${month}月`;
}
