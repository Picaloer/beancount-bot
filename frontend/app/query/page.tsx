"use client";

import { FormEvent, useMemo, useState } from "react";
import useSWRMutation from "swr/mutation";
import { askFinanceQuestion, type QueryAnswer } from "@/lib/api";

const EXAMPLES = [
  "我这个月总支出多少？",
  "上个月餐饮花了多少钱？",
  "这个月哪个类别花得最多？",
  "这个月花得最多的商家是谁？",
  "2026-03 一共有多少笔交易？",
];

export default function QueryPage() {
  const [question, setQuestion] = useState(EXAMPLES[0]);
  const [history, setHistory] = useState<QueryAnswer[]>([]);
  const [error, setError] = useState<string | null>(null);

  const { trigger, isMutating } = useSWRMutation(
    "finance-query",
    async (_key: string, { arg }: { arg: string }) => askFinanceQuestion(arg)
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed) {
      setError("请输入一个财务问题");
      return;
    }

    setError(null);
    try {
      const result = await trigger(trimmed);
      setHistory((current) => [result, ...current.filter((item) => item.question !== result.question)].slice(0, 6));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "查询失败");
    }
  }

  const latest = history[0] ?? null;
  const insightChips = useMemo(() => {
    if (!latest) {
      return [] as string[];
    }

    const chips = [`账期 ${latest.year_month}`, `意图 ${intentLabel(latest.intent)}`];
    if (typeof latest.data.total === "number") {
      chips.push(`金额 ¥${latest.data.total.toFixed(2)}`);
    }
    if (typeof latest.data.count === "number") {
      chips.push(`笔数 ${latest.data.count}`);
    }
    if (typeof latest.data.category_l1 === "string") {
      chips.push(`分类 ${latest.data.category_l1}`);
    }
    if (typeof latest.data.merchant === "string") {
      chips.push(`商家 ${latest.data.merchant}`);
    }
    return chips;
  }, [latest]);

  return (
    <div className="space-y-8">
      <section className="rounded-[32px] border border-stone-200 bg-[linear-gradient(145deg,rgba(255,251,245,0.96),rgba(244,236,223,0.92))] p-6 shadow-[0_20px_50px_rgba(97,72,38,0.09)]">
        <div className="space-y-4">
          <span className="inline-flex rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-amber-800">
            Finance Q&A
          </span>
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-stone-900">自然语言财务查询</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-stone-600">
              直接用中文提问，例如本月总支出、某个分类花了多少钱，或者哪个商家消费最多。当前版本支持高频月度问答，适合作为后续 NLQueryAgent 的第一步落地。
            </p>
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <section className="rounded-3xl border border-stone-200 bg-white/90 p-6 shadow-[0_18px_40px_rgba(84,62,34,0.06)]">
          <form className="space-y-4" onSubmit={handleSubmit}>
            <label className="block space-y-2">
              <span className="text-sm font-medium text-stone-700">输入问题</span>
              <textarea
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                rows={4}
                placeholder="例如：上个月餐饮花了多少钱？"
                className="w-full rounded-2xl border border-stone-300 bg-stone-50/70 px-4 py-3 text-sm leading-6 text-stone-900 outline-none transition-colors focus:border-amber-500"
              />
            </label>

            <div className="flex flex-wrap gap-2">
              {EXAMPLES.map((example) => (
                <button
                  key={example}
                  type="button"
                  onClick={() => setQuestion(example)}
                  className="rounded-full border border-stone-200 bg-stone-50 px-3 py-1.5 text-xs font-medium text-stone-600 transition-colors hover:border-amber-300 hover:text-amber-800"
                >
                  {example}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-3">
              <button
                type="submit"
                disabled={isMutating}
                className="rounded-xl bg-amber-700 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-amber-800 disabled:opacity-60"
              >
                {isMutating ? "查询中..." : "开始查询"}
              </button>
              <p className="text-xs text-stone-400">支持账期、分类、商家、收入、支出、净收支与交易数问题</p>
            </div>
          </form>

          {error && (
            <div className="mt-5 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <div className="mt-6 rounded-3xl border border-stone-200 bg-[linear-gradient(145deg,rgba(250,246,239,0.92),rgba(255,255,255,0.95))] p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-stone-400">最新回答</p>
                <h2 className="mt-2 text-lg font-semibold text-stone-900">{latest ? latest.question : "等待你的问题"}</h2>
              </div>
              {latest && (
                <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800">
                  {intentLabel(latest.intent)}
                </span>
              )}
            </div>

            {latest ? (
              <>
                <p className="mt-4 text-base leading-8 text-stone-700">{latest.answer}</p>
                <div className="mt-5 flex flex-wrap gap-2">
                  {insightChips.map((chip) => (
                    <span key={chip} className="rounded-full bg-stone-100 px-3 py-1 text-xs font-medium text-stone-600">
                      {chip}
                    </span>
                  ))}
                </div>
              </>
            ) : (
              <p className="mt-4 text-sm leading-6 text-stone-500">输入问题后，这里会返回账期识别、问答结果和关键数字。</p>
            )}
          </div>
        </section>

        <aside className="space-y-6 xl:sticky xl:top-24 xl:self-start">
          <section className="rounded-3xl border border-stone-200 bg-white/90 p-5 shadow-[0_18px_40px_rgba(84,62,34,0.06)]">
            <h2 className="text-lg font-semibold text-stone-900">支持的问题</h2>
            <div className="mt-4 space-y-3 text-sm text-stone-600">
              <p>总支出 / 总收入 / 净收支</p>
              <p>某个一级分类花了多少钱</p>
              <p>哪个分类支出最多</p>
              <p>哪个商家花得最多</p>
              <p>某月总交易笔数</p>
            </div>
          </section>

          <section className="rounded-3xl border border-stone-200 bg-white/90 p-5 shadow-[0_18px_40px_rgba(84,62,34,0.06)]">
            <h2 className="text-lg font-semibold text-stone-900">最近记录</h2>
            <div className="mt-4 space-y-3">
              {history.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-stone-200 px-4 py-6 text-center text-sm text-stone-400">
                  还没有查询记录
                </div>
              ) : (
                history.map((item) => (
                  <button
                    key={`${item.question}-${item.year_month}`}
                    type="button"
                    onClick={() => setQuestion(item.question)}
                    className="w-full rounded-2xl border border-stone-200 bg-stone-50/70 p-4 text-left transition-colors hover:border-amber-300"
                  >
                    <p className="line-clamp-2 text-sm font-medium text-stone-800">{item.question}</p>
                    <p className="mt-2 text-xs text-stone-500">{item.year_month} · {intentLabel(item.intent)}</p>
                  </button>
                ))
              )}
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}

function intentLabel(intent: string) {
  const labels: Record<string, string> = {
    total_expense: "总支出",
    total_income: "总收入",
    net: "净收支",
    transaction_count: "交易笔数",
    category_total: "分类支出",
    top_category: "最高支出分类",
    top_merchant: "最高支出商家",
  };
  return labels[intent] ?? intent;
}
