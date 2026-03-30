"use client";

import { FormEvent, useMemo, useState } from "react";
import useSWRMutation from "swr/mutation";

import Card from "@/app/components/Card";
import EmptyState from "@/app/components/EmptyState";
import PageHeader from "@/app/components/PageHeader";
import { askFinanceQuestion, type QueryAnswer } from "@/lib/api";

const EXAMPLES = [
  "我这个月总支出多少？",
  "上个月餐饮花了多少钱？",
  "这个月哪个类别花得最多？",
  "这个月花得最多的商家是谁？",
  "2026-03 一共有多少笔交易？",
];

const textareaClassName =
  "min-h-[148px] w-full rounded-2xl border border-[rgba(212,168,67,0.2)] bg-[var(--bg-elevated)] px-4 py-3 text-sm leading-7 text-[var(--text-primary)] outline-none transition placeholder:text-[var(--text-muted)] focus:border-[var(--gold-400)]";

const primaryButtonClassName =
  "inline-flex items-center justify-center rounded-xl bg-[var(--gold-400)] px-6 py-2.5 text-sm font-medium text-black transition hover:bg-[var(--gold-500)] disabled:cursor-not-allowed disabled:opacity-60";

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
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Natural Language Ledger"
        title="自然语言查账"
        description="像对账助手一样直接发问。输入一句中文，系统会识别账期和意图，再把答案装订成一张暗金答复卡。"
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-6">
          <Card variant="surface" className="p-6">
            <form className="space-y-4" onSubmit={handleSubmit}>
              <div>
                <h2 className="text-xl font-bold tracking-[-0.02em] text-[var(--text-primary)]">输入问题</h2>
                <p className="mt-2 text-sm leading-7 text-[var(--text-secondary)]">
                  支持账期、分类、商家、收入、支出、净收支与交易数问题。
                </p>
              </div>

              <textarea
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                rows={4}
                placeholder="例如：上个月餐饮花了多少钱？"
                className={textareaClassName}
              />

              <div className="flex flex-wrap gap-2">
                {EXAMPLES.map((example) => (
                  <button
                    key={example}
                    type="button"
                    onClick={() => setQuestion(example)}
                    className="rounded-full border border-[rgba(212,168,67,0.15)] bg-[var(--bg-elevated)] px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] transition hover:border-[var(--gold-400)] hover:text-[var(--gold-400)]"
                  >
                    {example}
                  </button>
                ))}
              </div>

              <button type="submit" disabled={isMutating} className={primaryButtonClassName}>
                {isMutating ? "查询中..." : "开始查询"}
              </button>
            </form>
          </Card>

          {error ? (
            <div className="rounded-[24px] border border-rose-400/20 bg-rose-400/8 px-4 py-3 text-sm text-rose-200">
              {error}
            </div>
          ) : null}

          <Card variant="elevated" className="p-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-[var(--text-muted)]">Latest Answer</p>
                <h2 className="mt-3 text-xl font-bold tracking-[-0.02em] text-[var(--text-primary)]">
                  {latest ? latest.question : "等待你的问题"}
                </h2>
              </div>
              {latest ? (
                <span className="rounded-full bg-[rgba(212,168,67,0.12)] px-3 py-1 text-xs font-medium text-[var(--gold-400)] ring-1 ring-inset ring-[rgba(212,168,67,0.2)]">
                  {intentLabel(latest.intent)}
                </span>
              ) : null}
            </div>

            {latest ? (
              <>
                <p className="mt-5 text-lg font-medium leading-9 text-[var(--text-primary)]">{latest.answer}</p>
                <div className="mt-5 flex flex-wrap gap-2">
                  {insightChips.map((chip) => (
                    <span
                      key={chip}
                      className="rounded-full border border-white/6 bg-[var(--bg-muted)] px-3 py-1 text-xs font-medium text-[var(--text-secondary)]"
                    >
                      {chip}
                    </span>
                  ))}
                </div>
              </>
            ) : (
              <EmptyState
                className="mt-6"
                title="答案卡仍是空白页"
                description="提一个关于金额、分类、商家或交易数量的问题，这里会返回解析结果和关键数字。"
              />
            )}
          </Card>
        </div>

        <aside className="space-y-6 xl:sticky xl:top-8 xl:self-start">
          <Card variant="surface" className="p-5">
            <h2 className="text-lg font-semibold text-[var(--text-primary)]">支持的问题</h2>
            <div className="mt-4 space-y-3 text-sm leading-7 text-[var(--text-secondary)]">
              <p>总支出 / 总收入 / 净收支</p>
              <p>某个一级分类花了多少钱</p>
              <p>哪个分类支出最多</p>
              <p>哪个商家花得最多</p>
              <p>某月总交易笔数</p>
            </div>
          </Card>

          <Card variant="surface" className="p-5">
            <h2 className="text-lg font-semibold text-[var(--text-primary)]">最近记录</h2>
            <div className="mt-4 space-y-3">
              {history.length === 0 ? (
                <EmptyState
                  className="p-6"
                  title="还没有查询记录"
                  description="提交第一个问题后，这里会保留最近几次提问，方便再次复用。"
                />
              ) : (
                history.map((item) => (
                  <button
                    key={`${item.question}-${item.year_month}`}
                    type="button"
                    onClick={() => setQuestion(item.question)}
                    className="w-full rounded-[22px] border border-[var(--border-subtle)] bg-[var(--bg-elevated)] p-4 text-left transition hover:border-[rgba(212,168,67,0.24)]"
                  >
                    <p className="line-clamp-2 text-sm font-medium text-[var(--text-primary)]">{item.question}</p>
                    <p className="mt-2 text-xs text-[var(--text-muted)]">
                      {item.year_month} / {intentLabel(item.intent)}
                    </p>
                  </button>
                ))
              )}
            </div>
          </Card>
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
