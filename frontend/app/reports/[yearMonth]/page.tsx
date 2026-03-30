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
import { getCategoryTrends, getMerchantRanking, getMonthlyReport } from "@/lib/api";

const COLORS = [
  "#9f5b2f",
  "#c9781f",
  "#2f7a5e",
  "#b5542f",
  "#41698c",
  "#9a4e64",
  "#7c6a41",
  "#556b2f",
];

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const currencyFormatter = new Intl.NumberFormat("zh-CN", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

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
    return <div className="py-24 text-center text-stone-400">正在整理本月账目与洞察...</div>;
  }

  if (!report) {
    return (
      <div className="py-24 text-center text-stone-400">
        <p>
          暂无数据，请先
          <Link href="/import" className="text-amber-700 hover:underline">
            导入账单
          </Link>
        </p>
      </div>
    );
  }

  const trendCategories = trends?.categories ?? [];
  const trendPoints = trends?.points ?? [];
  const trendWindow =
    trends && trends.months.length > 0
      ? `${formatYearMonth(trends.months[0])} - ${formatYearMonth(trends.months[trends.months.length - 1])}`
      : "最近 6 个月";

  return (
    <div className="space-y-8">
      <section className="rounded-[32px] border border-stone-200 bg-[linear-gradient(145deg,rgba(255,251,245,0.96),rgba(244,236,223,0.92))] p-6 shadow-[0_20px_50px_rgba(97,72,38,0.09)]">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-3">
            <Link href="/reports" className="inline-flex items-center text-sm text-stone-500 transition-colors hover:text-amber-700">
              返回所有报告
            </Link>
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-3">
                <h1 className="text-3xl font-bold tracking-tight text-stone-900">{ym} 财务报告</h1>
                <span
                  className={`rounded-full px-3 py-1 text-xs font-medium ${
                    report.cached ? "bg-stone-200 text-stone-700" : "bg-amber-100 text-amber-800"
                  }`}
                >
                  {report.cached ? "缓存结果" : "实时生成"}
                </span>
              </div>
              <p className="max-w-2xl text-sm leading-6 text-stone-600">
                从支出结构、周度波动到商家排行，快速看清这个月的钱流向了哪里，以及过去半年里哪些分类正在持续抬升。
              </p>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <a
              href={`${API_BASE}/reports/beancount/${ym}`}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-xl border border-stone-300 px-4 py-2 text-sm font-medium text-stone-700 transition-colors hover:border-amber-500 hover:text-amber-800"
            >
              导出 Beancount
            </a>
            <button
              type="button"
              onClick={() => mutate(getMonthlyReport(ym, true))}
              className="rounded-xl bg-amber-700 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-amber-800"
            >
              重新生成
            </button>
          </div>
        </div>
      </section>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="总支出" value={formatCurrency(report.total_expense)} tone="rose" />
        <StatCard label="总收入" value={formatCurrency(report.total_income)} tone="emerald" />
        <StatCard
          label="净收支"
          value={`${report.net >= 0 ? "+" : ""}${formatCurrency(report.net)}`}
          tone={report.net >= 0 ? "amber" : "stone"}
        />
        <StatCard label="交易笔数" value={`${report.transaction_count} 笔`} tone="sky" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <section className="rounded-3xl border border-stone-200 bg-white/90 p-5 shadow-[0_18px_40px_rgba(84,62,34,0.06)]">
          <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-stone-900">近 6 个月分类消费趋势</h2>
              <p className="mt-1 text-sm text-stone-500">观察高频支出分类的月度变化，判断哪些开销正在持续走高。</p>
            </div>
            <span className="text-xs uppercase tracking-[0.18em] text-stone-400">{trendWindow}</span>
          </div>

          {trendCategories.length === 0 ? (
            <div className="flex h-[320px] items-center justify-center rounded-2xl border border-dashed border-stone-200 bg-stone-50/70 text-sm text-stone-400">
              历史月份不足，继续导入账单后可查看趋势变化
            </div>
          ) : (
            <>
              <div className="mb-4 flex flex-wrap gap-2">
                {trendCategories.map((category, index) => (
                  <span
                    key={category}
                    className="inline-flex items-center gap-2 rounded-full bg-stone-100 px-3 py-1 text-xs font-medium text-stone-700"
                  >
                    <span
                      className="h-2.5 w-2.5 rounded-full"
                      style={{ backgroundColor: COLORS[index % COLORS.length] }}
                    />
                    {category}
                  </span>
                ))}
              </div>
              <ResponsiveContainer width="100%" height={320}>
                <LineChart data={trendPoints} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#ece3d5" />
                  <XAxis
                    dataKey="year_month"
                    tickFormatter={formatMonthTick}
                    tick={{ fontSize: 12, fill: "#6b6258" }}
                    axisLine={{ stroke: "#d7caba" }}
                    tickLine={{ stroke: "#d7caba" }}
                  />
                  <YAxis
                    tickFormatter={formatAxisCurrency}
                    tick={{ fontSize: 12, fill: "#6b6258" }}
                    axisLine={{ stroke: "#d7caba" }}
                    tickLine={{ stroke: "#d7caba" }}
                    width={72}
                  />
                  <Tooltip
                    labelFormatter={(value) => formatYearMonth(String(value))}
                    formatter={(value, name) => [formatCurrency(Number(value ?? 0)), String(name ?? "")]}
                    contentStyle={{
                      borderRadius: 16,
                      borderColor: "#dccfbf",
                      boxShadow: "0 12px 30px rgba(89, 66, 35, 0.12)",
                    }}
                  />
                  {trendCategories.map((category, index) => (
                    <Line
                      key={category}
                      type="monotone"
                      dataKey={category}
                      stroke={COLORS[index % COLORS.length]}
                      strokeWidth={2.5}
                      dot={{ r: 3, strokeWidth: 0 }}
                      activeDot={{ r: 5 }}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </>
          )}
        </section>

        <section className="rounded-3xl border border-stone-200 bg-white/90 p-5 shadow-[0_18px_40px_rgba(84,62,34,0.06)]">
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-stone-900">趋势焦点</h2>
            <p className="mt-1 text-sm text-stone-500">按近 6 个月累计金额选出最值得关注的分类。</p>
          </div>

          <div className="space-y-3">
            {(trends?.top_categories ?? []).length === 0 ? (
              <div className="rounded-2xl border border-dashed border-stone-200 px-4 py-6 text-center text-sm text-stone-400">
                暂无趋势数据
              </div>
            ) : (
              (trends?.top_categories ?? []).map((item, index) => (
                <div key={item.category_l1} className="rounded-2xl border border-stone-200 bg-stone-50/70 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="flex items-center gap-2 font-medium text-stone-800">
                        <span
                          className="h-2.5 w-2.5 rounded-full"
                          style={{ backgroundColor: COLORS[index % COLORS.length] }}
                        />
                        <span className="truncate">{item.category_l1}</span>
                      </p>
                      <p className="mt-1 text-xs uppercase tracking-[0.16em] text-stone-400">近 6 个月累计</p>
                    </div>
                    <span className="text-sm font-semibold text-stone-900">{formatCurrency(item.total)}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-3xl border border-stone-200 bg-white/90 p-5 shadow-[0_18px_40px_rgba(84,62,34,0.06)]">
          <h2 className="mb-4 text-lg font-semibold text-stone-900">支出分类占比</h2>
          {report.category_breakdown.length === 0 ? (
            <p className="py-16 text-center text-sm text-stone-400">暂无支出数据</p>
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
                    <Cell key={index} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value, name) => [formatCurrency(Number(value ?? 0)), String(name ?? "金额")]} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </section>

        <section className="rounded-3xl border border-stone-200 bg-white/90 p-5 shadow-[0_18px_40px_rgba(84,62,34,0.06)]">
          <h2 className="mb-4 text-lg font-semibold text-stone-900">按周支出分布</h2>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={report.weekly_expense} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ece3d5" />
              <XAxis
                dataKey="week"
                tickFormatter={(value) => `第${value}周`}
                tick={{ fontSize: 12, fill: "#6b6258" }}
                axisLine={{ stroke: "#d7caba" }}
                tickLine={{ stroke: "#d7caba" }}
              />
              <YAxis
                tick={{ fontSize: 12, fill: "#6b6258" }}
                tickFormatter={formatAxisCurrency}
                axisLine={{ stroke: "#d7caba" }}
                tickLine={{ stroke: "#d7caba" }}
                width={72}
              />
              <Tooltip formatter={(value, name) => [formatCurrency(Number(value ?? 0)), String(name ?? "支出")]} />
              <Bar dataKey="amount" fill="#a7652c" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </section>
      </div>

      <section className="overflow-hidden rounded-3xl border border-stone-200 bg-white/90 shadow-[0_18px_40px_rgba(84,62,34,0.06)]">
        <div className="border-b border-stone-100 px-5 py-4">
          <h2 className="text-lg font-semibold text-stone-900">分类支出明细</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-stone-50 text-xs uppercase tracking-wide text-stone-500">
              <tr>
                <th className="px-5 py-3 text-left">分类</th>
                <th className="px-5 py-3 text-right">金额</th>
                <th className="px-5 py-3 text-right">占比</th>
                <th className="px-5 py-3">趋势条</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {report.category_breakdown.map((cat, index) => (
                <tr key={cat.category_l1} className="hover:bg-amber-50/40">
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2 text-stone-800">
                      <span
                        className="inline-block h-3 w-3 rounded-full"
                        style={{ backgroundColor: COLORS[index % COLORS.length] }}
                      />
                      <span>{cat.category_l1}</span>
                    </div>
                  </td>
                  <td className="px-5 py-3 text-right font-medium text-stone-900">{formatCurrency(cat.amount)}</td>
                  <td className="px-5 py-3 text-right text-stone-500">{cat.percentage}%</td>
                  <td className="px-5 py-3">
                    <div className="mx-auto h-2 w-36 rounded-full bg-stone-100">
                      <div
                        className="h-2 rounded-full"
                        style={{
                          width: `${cat.percentage}%`,
                          backgroundColor: COLORS[index % COLORS.length],
                        }}
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {(ranking ?? []).length > 0 && (
        <section className="overflow-hidden rounded-3xl border border-stone-200 bg-white/90 shadow-[0_18px_40px_rgba(84,62,34,0.06)]">
          <div className="border-b border-stone-100 px-5 py-4">
            <h2 className="text-lg font-semibold text-stone-900">商家支出排行榜 TOP 10</h2>
          </div>
          <div className="divide-y divide-stone-100">
            {(ranking ?? []).map((merchant, index) => (
              <div key={merchant.merchant} className="flex items-center gap-4 px-5 py-3 hover:bg-amber-50/40">
                <span
                  className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold ${
                    index < 3 ? "bg-amber-100 text-amber-800" : "bg-stone-100 text-stone-500"
                  }`}
                >
                  {index + 1}
                </span>
                <span className="flex-1 truncate text-sm text-stone-800">{merchant.merchant}</span>
                <span className="text-sm text-stone-500">{merchant.count} 笔</span>
                <span className="text-sm font-semibold text-stone-900">{formatCurrency(merchant.total)}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {report.ai_insight && (
        <section className="rounded-3xl border border-amber-200 bg-[linear-gradient(145deg,rgba(255,248,235,0.95),rgba(246,234,213,0.9))] p-6 shadow-[0_18px_40px_rgba(108,78,33,0.08)]">
          <div className="mb-3 flex items-center gap-3">
            <div className="rounded-2xl bg-amber-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-amber-800">
              AI Insight
            </div>
            <h2 className="text-lg font-semibold text-stone-900">本月财务洞察</h2>
          </div>
          <p className="text-sm leading-7 text-stone-700">{report.ai_insight}</p>
        </section>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "rose" | "emerald" | "amber" | "stone" | "sky";
}) {
  const toneClasses: Record<string, string> = {
    rose: "bg-rose-50 text-rose-700 border-rose-100",
    emerald: "bg-emerald-50 text-emerald-700 border-emerald-100",
    amber: "bg-amber-50 text-amber-800 border-amber-100",
    stone: "bg-stone-100 text-stone-700 border-stone-200",
    sky: "bg-sky-50 text-sky-700 border-sky-100",
  };

  return (
    <div className={`rounded-3xl border p-5 shadow-[0_16px_36px_rgba(84,62,34,0.05)] ${toneClasses[tone]}`}>
      <p className="text-xs uppercase tracking-[0.16em] text-stone-500">{label}</p>
      <p className="mt-3 text-2xl font-bold">{value}</p>
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
