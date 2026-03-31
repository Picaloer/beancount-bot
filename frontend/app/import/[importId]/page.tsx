"use client";

import { use, useMemo, useState } from "react";
import Link from "next/link";
import useSWR from "swr";

import { SourceBadge, StatusBadge } from "@/app/components/Badge";
import Card, { cx } from "@/app/components/Card";
import EmptyState from "@/app/components/EmptyState";
import PageHeader from "@/app/components/PageHeader";
import ProgressBar from "@/app/components/ProgressBar";
import {
  getImportDetail,
  resolveDuplicateReviewGroup,
  type DuplicateReviewGroup,
  type ImportDetail,
  type ImportLifecycleStatus,
  type ImportStage,
} from "@/lib/api";

const primaryButtonClassName =
  "inline-flex items-center justify-center rounded-xl bg-[var(--gold-400)] px-4 py-2.5 text-sm font-medium text-black transition hover:bg-[var(--gold-500)] disabled:cursor-not-allowed disabled:opacity-60";

const secondaryButtonClassName =
  "inline-flex items-center justify-center rounded-xl border border-[rgba(212,168,67,0.28)] bg-[rgba(255,255,255,0.02)] px-4 py-2.5 text-sm font-medium text-[var(--gold-400)] transition hover:bg-[rgba(212,168,67,0.08)] hover:text-[var(--text-primary)] disabled:cursor-not-allowed disabled:opacity-60";

export default function ImportDetailPage({
  params,
}: {
  params: Promise<{ importId: string }>;
}) {
  const { importId } = use(params);
  const [reviewingGroupId, setReviewingGroupId] = useState<string | null>(null);
  const [selectedTransactions, setSelectedTransactions] = useState<Record<string, string>>({});
  const [reviewMessages, setReviewMessages] = useState<Record<string, string>>({});
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [reviewNotice, setReviewNotice] = useState<string | null>(null);
  const { data, error, mutate } = useSWR<ImportDetail>(["import-detail", importId], () => getImportDetail(importId), {
    refreshInterval: (detail) => (detail && isTerminalStatus(detail.status) ? 0 : 2000),
  });

  const pendingGroupIds = useMemo(
    () => data?.duplicate_review.groups.filter((group) => group.review_status === "pending").map((group) => group.group_id) ?? [],
    [data]
  );

  async function handleResolveGroup(group: DuplicateReviewGroup) {
    const keptTransactionId = selectedTransactions[group.group_id] ?? group.transactions[0]?.transaction_id;
    if (!keptTransactionId) {
      setReviewError("当前分组缺少可保留的候选交易");
      return;
    }

    setReviewError(null);
    setReviewNotice(null);
    setReviewingGroupId(group.group_id);
    try {
      await resolveDuplicateReviewGroup(importId, group.group_id, {
        kept_transaction_id: keptTransactionId,
        review_reason: reviewMessages[group.group_id]?.trim() || undefined,
      });
      const remainingPendingCount = Math.max(pendingGroupIds.length - 1, 0);
      setReviewNotice(
        remainingPendingCount > 0
          ? `已完成 1 组复核，仍有 ${remainingPendingCount} 组待确认。`
          : "已完成最后一组复核，系统正在继续分类与生成分录。"
      );
      setReviewMessages((current) => {
        const next = { ...current };
        delete next[group.group_id];
        return next;
      });
      await mutate();
    } catch (e: unknown) {
      setReviewError(e instanceof Error ? e.message : "提交复核结果失败");
    } finally {
      setReviewingGroupId(null);
    }
  }

  if (error) {
    return (
      <div className="mx-auto max-w-6xl space-y-6">
        <PageHeader
          eyebrow="Import Ledger"
          title="导入详情"
          description="查看单次导入的阶段时间线、AI 分类进度，以及导入后产出的结构化摘要。"
        >
          <Link href="/import" className={secondaryButtonClassName}>
            返回导入页
          </Link>
        </PageHeader>

        <EmptyState title="未找到这次导入" description={error.message || "该导入记录不存在，或已被删除。"} />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="mx-auto max-w-6xl space-y-6">
        <PageHeader
          eyebrow="Import Ledger"
          title="导入详情"
          description="查看单次导入的阶段时间线、AI 分类进度，以及导入后产出的结构化摘要。"
        >
          <Link href="/import" className={secondaryButtonClassName}>
            返回导入页
          </Link>
        </PageHeader>

        <LoadingDetail />
      </div>
    );
  }

  const progress = getImportProgressValue(data);
  const done = data.status === "done";
  const failed = data.status === "failed";

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Import Ledger"
        title="导入详情"
        description="查看单次导入的阶段时间线、AI 分类进度，以及导入后产出的结构化摘要。"
      >
        <div className="flex flex-wrap items-center gap-3">
          {done ? (
            <Link href="/transactions" className={primaryButtonClassName}>
              查看交易
            </Link>
          ) : null}
          <Link href="/import" className={secondaryButtonClassName}>
            返回导入页
          </Link>
        </div>
      </PageHeader>

      <Card variant={failed ? "bordered" : "surface"} className="p-6 sm:p-7">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="truncate text-2xl font-bold tracking-[-0.03em] text-[var(--text-primary)]">
                {data.file_name}
              </h2>
              <SourceBadge source={data.source} />
              <StatusBadge status={data.status} />
            </div>
            <p className="mt-3 text-sm leading-7 text-[var(--text-secondary)]">
              导入于 {formatImportTime(data.imported_at)}
              <span className="mx-2 text-[var(--text-muted)]">/</span>
              来源 {sourceLabel(data.source)}
            </p>
            {data.stage_message ? (
              <p className="mt-2 text-sm text-[var(--text-muted)]">{data.stage_message}</p>
            ) : null}
            {failed && data.error_message ? (
              <div className="mt-5 rounded-[22px] border border-rose-400/20 bg-rose-400/8 px-4 py-4 text-sm leading-7 text-rose-200">
                {data.error_message}
              </div>
            ) : null}
          </div>

          <div className="grid min-w-0 gap-3 sm:grid-cols-2 xl:w-[360px] xl:grid-cols-1">
            <MetricChip label="开始时间" value={data.started_at ? formatImportTime(data.started_at) : "—"} />
            <MetricChip label="完成时间" value={data.finished_at ? formatImportTime(data.finished_at) : "—"} />
            <MetricChip label="累计 Token" value={formatNumber(data.total_tokens)} />
          </div>
        </div>

        <div className="mt-6 grid gap-5 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,0.7fr)]">
          <div className="rounded-[24px] border border-[var(--border-subtle)] bg-[rgba(255,255,255,0.03)] p-4">
            <ProgressBar
              label="整体进度"
              tone={done ? "healthy" : failed ? "overspent" : "gold"}
              value={progress}
              valueLabel={`${progress.toFixed(0)}%`}
            />
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <MetricChip
                label="已处理交易"
                value={`${data.processed_rows}/${Math.max(data.total_rows, data.row_count, 0)}`}
              />
              <MetricChip label="LLM 批次" value={`${data.llm_completed_batches}/${data.llm_total_batches}`} />
              <MetricChip label="写入交易" value={formatNumber(data.summary.inserted_count)} />
            </div>
          </div>

          <Card variant="elevated" className="p-4">
            <p className="text-xs uppercase tracking-[0.24em] text-[var(--gold-400)]">Pipeline State</p>
            <div className="mt-4 space-y-3">
              <StageSnapshot stage={getCurrentActiveStage(data.stages)} />
            </div>
          </Card>
        </div>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
        <section className="space-y-4">
          <Card variant="surface" className="p-6">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-xl font-bold tracking-[-0.02em] text-[var(--text-primary)]">阶段时间线</h2>
                <p className="mt-1 text-sm text-[var(--text-secondary)]">
                  从解析到账务分录生成，完整保留每个阶段的状态与消息。
                </p>
              </div>
              <span className="rounded-full bg-white/5 px-3 py-1 text-xs text-[var(--text-muted)]">
                {data.stages.length} 个阶段
              </span>
            </div>

            <div className="mt-6 space-y-4">
              {data.stages.map((stage, index) => {
                const tone = stageTone(stage.status);
                const complete = stage.status === "done";
                const active = stage.status === "processing";
                const failedStage = stage.status === "failed";

                return (
                  <div key={`${stage.stage_key}-${index}`} className="flex gap-4">
                    <div className="flex flex-col items-center">
                      <div
                        className={cx(
                          "flex h-11 w-11 items-center justify-center rounded-full border text-sm font-semibold",
                          tone.circle
                        )}
                      >
                        {complete ? "✓" : failedStage ? "!" : index + 1}
                      </div>
                      {index < data.stages.length - 1 ? (
                        <div className={cx("mt-2 h-full min-h-12 w-px", complete ? "bg-[var(--gold-400)]/55" : "bg-white/8")} />
                      ) : null}
                    </div>

                    <div className="min-w-0 flex-1 rounded-[24px] border border-[var(--border-subtle)] bg-[rgba(255,255,255,0.03)] p-4">
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <h3 className="text-base font-semibold text-[var(--text-primary)]">{stage.stage_label}</h3>
                            <span className={cx("rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset", tone.badge)}>
                              {stageStatusLabel(stage.status)}
                            </span>
                            {active ? (
                              <span className="rounded-full bg-[rgba(212,168,67,0.1)] px-2.5 py-1 text-xs font-medium text-[var(--gold-400)] ring-1 ring-inset ring-[rgba(212,168,67,0.22)]">
                                进行中
                              </span>
                            ) : null}
                          </div>
                          <p className="mt-2 text-sm leading-7 text-[var(--text-secondary)]">
                            {stage.message || defaultStageMessage(stage)}
                          </p>
                        </div>

                        <div className="grid gap-2 text-sm text-[var(--text-muted)] sm:min-w-[168px] sm:text-right">
                          <span>{stage.started_at ? `开始：${formatImportTime(stage.started_at)}` : "开始：—"}</span>
                          <span>{stage.finished_at ? `结束：${formatImportTime(stage.finished_at)}` : "结束：—"}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>

          <Card variant="surface" className="p-6">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-xl font-bold tracking-[-0.02em] text-[var(--text-primary)]">疑似重复分组</h2>
                <p className="mt-1 text-sm text-[var(--text-secondary)]">
                  展示本次导入中跨来源且同日同金额的候选交易，便于后续人工确认。
                </p>
              </div>
              <span className="rounded-full bg-white/5 px-3 py-1 text-xs text-[var(--text-muted)]">
                {data.duplicate_review.group_count} 组
              </span>
            </div>

            {reviewError ? (
              <div className="mt-6 rounded-[22px] border border-rose-400/20 bg-rose-400/8 px-4 py-4 text-sm leading-7 text-rose-200">
                {reviewError}
              </div>
            ) : null}

            {reviewNotice ? (
              <div className="mt-4 rounded-[22px] border border-emerald-400/20 bg-emerald-400/8 px-4 py-4 text-sm leading-7 text-emerald-100">
                {reviewNotice}
              </div>
            ) : null}

            {data.duplicate_review.groups.length === 0 ? (
              <div className="mt-6">
                <EmptyState
                  title="没有待复核分组"
                  description="系统没有发现需要人工确认的跨来源疑似重复交易。"
                />
              </div>
            ) : (
              <div className="mt-6 space-y-4">
                {data.duplicate_review.groups.map((group) => (
                  <DuplicateReviewGroupCard
                    key={group.group_id}
                    group={group}
                    reviewing={reviewingGroupId === group.group_id}
                    selectedTransactionId={selectedTransactions[group.group_id] ?? group.transactions[0]?.transaction_id ?? null}
                    reviewMessage={reviewMessages[group.group_id] ?? ""}
                    onSelectTransaction={(transactionId) => {
                      setSelectedTransactions((current) => ({
                        ...current,
                        [group.group_id]: transactionId,
                      }));
                    }}
                    onReviewMessageChange={(message) => {
                      setReviewMessages((current) => ({
                        ...current,
                        [group.group_id]: message,
                      }));
                    }}
                    onResolve={() => void handleResolveGroup(group)}
                  />
                ))}
              </div>
            )}
          </Card>
        </section>

        <aside className="space-y-4 xl:sticky xl:top-8 xl:self-start">
          <Card variant="elevated" className="p-5">
            <p className="text-xs uppercase tracking-[0.24em] text-[var(--gold-400)]">Import Summary</p>
            <h2 className="mt-4 text-xl font-bold tracking-[-0.02em] text-[var(--text-primary)]">导入结果摘要</h2>
            <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
              <SummaryMetric label="新增交易" value={data.summary.inserted_count} tone="gold" />
              <SummaryMetric label="识别重复" value={data.summary.duplicate_count} tone="info" />
              <SummaryMetric label="待复核分组" value={data.summary.duplicate_review_group_count} tone="warning" />
              <SummaryMetric label="待复核配对" value={data.summary.duplicate_review_pair_count} tone="warning" />
              <SummaryMetric label="已完成复核" value={data.summary.duplicate_review_resolved_count} tone="healthy" />
              <SummaryMetric label="Beancount 分录" value={data.summary.beancount_entry_count} tone="healthy" />
              <SummaryMetric label="规则分类" value={data.summary.rule_based_count} tone="healthy" />
              <SummaryMetric label="AI 分类" value={data.summary.llm_based_count} tone="gold" />
              <SummaryMetric label="兜底分类" value={data.summary.fallback_count} tone="warning" />
              <SummaryMetric label="低置信度" value={data.summary.low_confidence_count} tone="overspent" />
            </div>
          </Card>

          <Card variant="surface" className="p-5">
            <p className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Duplicate Review</p>
            <h2 className="mt-4 text-xl font-bold tracking-[-0.02em] text-[var(--text-primary)]">疑似重复复核</h2>
            <div className="mt-5 grid gap-3">
              <MetricChip label="分组数量" value={formatNumber(data.duplicate_review.group_count)} />
              <MetricChip label="待处理" value={formatNumber(data.duplicate_review.pending_count)} />
              <MetricChip label="已处理" value={formatNumber(data.duplicate_review.resolved_count)} />
            </div>
            {data.duplicate_review.pending_count > 0 ? (
              <div className="mt-4 rounded-[22px] border border-amber-400/20 bg-amber-400/8 px-4 py-4 text-sm leading-7 text-amber-100">
                当前导入已暂停，等待人工确认这些跨来源且同日同金额的疑似重复交易。
              </div>
            ) : data.duplicate_review.group_count === 0 ? (
              <p className="mt-4 text-sm leading-7 text-[var(--text-secondary)]">
                这次导入没有发现需要人工复核的跨来源疑似重复交易。
              </p>
            ) : null}
          </Card>

          <Card variant="surface" className="p-5">
            <p className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Token Ledger</p>
            <div className="mt-5 grid gap-3">
              <MetricChip label="输入 Token" value={formatNumber(data.input_tokens)} />
              <MetricChip label="输出 Token" value={formatNumber(data.output_tokens)} />
              <MetricChip label="总 Token" value={formatNumber(data.total_tokens)} />
            </div>
          </Card>
        </aside>
      </div>
    </div>
  );
}

function LoadingDetail() {
  return (
    <Card variant="surface" className="p-6">
      <div className="grid gap-4 lg:grid-cols-3">
        {Array.from({ length: 3 }).map((_, index) => (
          <div key={index} className="rounded-[24px] border border-white/8 bg-white/3 p-4">
            <div className="h-4 w-24 animate-pulse rounded bg-white/8" />
            <div className="mt-4 h-9 w-32 animate-pulse rounded bg-white/8" />
            <div className="mt-3 h-3 w-28 animate-pulse rounded bg-white/8" />
          </div>
        ))}
      </div>
      <div className="mt-6 space-y-3">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="rounded-[24px] border border-white/8 bg-white/3 p-4">
            <div className="h-4 w-40 animate-pulse rounded bg-white/8" />
            <div className="mt-3 h-3 w-full animate-pulse rounded bg-white/8" />
            <div className="mt-2 h-3 w-2/3 animate-pulse rounded bg-white/8" />
          </div>
        ))}
      </div>
    </Card>
  );
}

function StageSnapshot({ stage }: { stage: ImportStage | null }) {
  if (!stage) {
    return <p className="text-sm leading-7 text-[var(--text-secondary)]">阶段信息暂未生成。</p>;
  }

  return (
    <>
      <div className="rounded-[22px] border border-[var(--border-subtle)] bg-[rgba(255,255,255,0.03)] p-4">
        <div className="flex items-center justify-between gap-3">
          <span className="text-sm font-medium text-[var(--text-secondary)]">当前阶段</span>
          <span className="rounded-full bg-[rgba(212,168,67,0.1)] px-2.5 py-1 text-xs font-medium text-[var(--gold-400)] ring-1 ring-inset ring-[rgba(212,168,67,0.22)]">
            {stageStatusLabel(stage.status)}
          </span>
        </div>
        <p className="mt-4 text-lg font-semibold text-[var(--text-primary)]">{stage.stage_label}</p>
        <p className="mt-2 text-sm leading-7 text-[var(--text-secondary)]">{stage.message || defaultStageMessage(stage)}</p>
      </div>
    </>
  );
}

function SummaryMetric({
  label,
  tone,
  value,
}: {
  label: string;
  tone: "gold" | "healthy" | "warning" | "overspent" | "info";
  value: number;
}) {
  const toneClassName: Record<typeof tone, string> = {
    gold: "text-[var(--gold-400)] bg-[rgba(212,168,67,0.08)] border-[rgba(212,168,67,0.16)]",
    healthy: "text-emerald-300 bg-emerald-400/8 border-emerald-400/16",
    warning: "text-amber-300 bg-amber-400/8 border-amber-400/16",
    overspent: "text-rose-300 bg-rose-400/8 border-rose-400/16",
    info: "text-sky-300 bg-sky-400/8 border-sky-400/16",
  };

  return (
    <div className={cx("rounded-[22px] border p-4", toneClassName[tone])}>
      <p className="text-xs uppercase tracking-[0.18em] opacity-80">{label}</p>
      <p className="mt-3 tabular text-3xl font-bold tracking-[-0.03em]">{formatNumber(value)}</p>
    </div>
  );
}

function MetricChip({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[22px] border border-[var(--border-subtle)] bg-[rgba(255,255,255,0.03)] px-4 py-3">
      <p className="text-xs uppercase tracking-[0.16em] text-[var(--text-muted)]">{label}</p>
      <p className="mt-2 text-sm font-medium text-[var(--text-primary)]">{value}</p>
    </div>
  );
}

function DuplicateReviewGroupCard({
  group,
  reviewing,
  selectedTransactionId,
  reviewMessage,
  onSelectTransaction,
  onReviewMessageChange,
  onResolve,
}: {
  group: DuplicateReviewGroup;
  reviewing: boolean;
  selectedTransactionId: string | null;
  reviewMessage: string;
  onSelectTransaction: (transactionId: string) => void;
  onReviewMessageChange: (message: string) => void;
  onResolve: () => void;
}) {
  const pending = group.review_status === "pending";

  return (
    <div className="rounded-[24px] border border-[var(--border-subtle)] bg-[rgba(255,255,255,0.03)] p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-base font-semibold text-[var(--text-primary)]">
              {group.candidate_date} / {formatCurrency(group.candidate_amount, group.candidate_currency)}
            </p>
            <span className={cx("rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset", reviewStatusTone(group.review_status))}>
              {reviewStatusLabel(group.review_status)}
            </span>
            {group.ai_suggestion ? (
              <span className="rounded-full bg-[rgba(212,168,67,0.1)] px-2.5 py-1 text-xs font-medium text-[var(--gold-400)] ring-1 ring-inset ring-[rgba(212,168,67,0.22)]">
                AI: {group.ai_suggestion}
                {group.ai_confidence !== null ? ` · ${Math.round(group.ai_confidence * 100)}%` : ""}
              </span>
            ) : null}
          </div>
          <p className="mt-2 text-sm leading-7 text-[var(--text-secondary)]">{group.review_reason || "等待人工确认该组候选交易。"}</p>
          {group.ai_reason ? (
            <p className="mt-2 text-sm leading-7 text-[var(--text-muted)]">{group.ai_reason}</p>
          ) : null}
        </div>

        <div className="grid gap-2 text-sm text-[var(--text-muted)] lg:min-w-[180px] lg:text-right">
          <span>候选交易：{formatNumber(group.transaction_count)} 条</span>
          <span>已处理时间：{group.resolved_at ? formatImportTime(group.resolved_at) : "—"}</span>
        </div>
      </div>

      <div className="mt-4 grid gap-3">
        {group.transactions.map((transaction) => {
          const selected = selectedTransactionId === transaction.transaction_id;

          return (
            <label
              key={transaction.transaction_id}
              className={cx(
                "block rounded-[20px] border bg-[var(--bg-elevated)] px-4 py-4 transition",
                pending
                  ? selected
                    ? "border-[rgba(212,168,67,0.32)] ring-1 ring-[rgba(212,168,67,0.18)]"
                    : "border-[var(--border-subtle)] hover:border-[rgba(212,168,67,0.2)]"
                  : "border-[var(--border-subtle)]"
              )}
            >
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-3">
                    {pending ? (
                      <input
                        type="radio"
                        name={`duplicate-review-${group.group_id}`}
                        value={transaction.transaction_id}
                        checked={selected}
                        onChange={() => onSelectTransaction(transaction.transaction_id)}
                        disabled={reviewing}
                        className="h-4 w-4 border-[var(--border-subtle)] bg-[var(--bg-muted)] text-[var(--gold-400)] focus:ring-[var(--gold-400)]"
                      />
                    ) : null}
                    <SourceBadge source={transaction.source} />
                    <span className="rounded-full bg-white/5 px-2.5 py-1 text-xs text-[var(--text-muted)]">
                      {reviewStatusLabel(transaction.duplicate_review_status)}
                    </span>
                    {pending && selected ? (
                      <span className="rounded-full bg-[rgba(212,168,67,0.1)] px-2.5 py-1 text-xs font-medium text-[var(--gold-400)] ring-1 ring-inset ring-[rgba(212,168,67,0.22)]">
                        保留此条
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-3 text-sm font-medium text-[var(--text-primary)]">{transaction.merchant || "未识别商户"}</p>
                  <p className="mt-2 text-sm leading-7 text-[var(--text-secondary)]">{transaction.description || "—"}</p>
                </div>

                <div className="grid gap-2 text-sm text-[var(--text-muted)] sm:min-w-[180px] sm:text-right">
                  <span className="tabular text-base font-semibold text-[var(--text-primary)]">
                    {formatCurrency(transaction.amount, transaction.currency)}
                  </span>
                  <span>{formatImportTime(transaction.transaction_at)}</span>
                </div>
              </div>
            </label>
          );
        })}
      </div>

      {pending ? (
        <div className="mt-4 rounded-[22px] border border-[rgba(212,168,67,0.16)] bg-[rgba(212,168,67,0.05)] p-4">
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
            <div>
              <label className="text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">复核说明（可选）</label>
              <textarea
                value={reviewMessage}
                onChange={(event) => onReviewMessageChange(event.target.value)}
                placeholder="例如：保留微信账单记录，支付宝为重复同步账单"
                disabled={reviewing}
                rows={3}
                className="mt-2 w-full rounded-[18px] border border-[rgba(212,168,67,0.18)] bg-[var(--bg-muted)] px-4 py-3 text-sm leading-7 text-[var(--text-primary)] outline-none transition placeholder:text-[var(--text-muted)] focus:border-[var(--gold-400)]"
              />
            </div>

            <button
              type="button"
              onClick={onResolve}
              disabled={reviewing || !selectedTransactionId}
              className={primaryButtonClassName}
            >
              {reviewing ? "提交中..." : "确认保留并继续"}
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function getCurrentActiveStage(stages: ImportStage[]) {
  return (
    stages.find((stage) => stage.status === "processing") ??
    [...stages].reverse().find((stage) => stage.status === "failed") ??
    [...stages].reverse().find((stage) => stage.status === "done") ??
    stages[0] ??
    null
  );
}

function getImportProgressValue(status: ImportDetail) {
  const denominator = Math.max(status.total_rows, status.row_count, 0);
  if (status.status === "done") return 100;
  if (status.status === "failed") return Math.max(8, Math.min(96, denominator > 0 ? (status.processed_rows / denominator) * 100 : 12));
  if (status.status === "pending") return 6;
  if (status.status === "processing") return denominator > 0 ? Math.min(32, (status.processed_rows / denominator) * 18 + 14) : 18;
  if (status.status === "reviewing_duplicates") return 52;
  if (status.status === "classifying") {
    if (status.llm_total_batches > 0) {
      return Math.min(88, 52 + (status.llm_completed_batches / status.llm_total_batches) * 36);
    }
    return denominator > 0 ? Math.min(88, 52 + (status.processed_rows / denominator) * 36) : 64;
  }
  return 0;
}

function isTerminalStatus(status: ImportLifecycleStatus) {
  return status === "done" || status === "failed";
}

function formatImportTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("zh-CN").format(value);
}

function formatCurrency(amount: number, currency: string) {
  return `${currency} ${new Intl.NumberFormat("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)}`;
}

function sourceLabel(source: string) {
  return {
    wechat: "微信支付",
    alipay: "支付宝",
    cmb: "招商银行",
  }[source] ?? source;
}

function stageStatusLabel(status: string) {
  return {
    pending: "等待中",
    processing: "处理中",
    done: "已完成",
    failed: "失败",
  }[status] ?? (status === "reviewing_duplicates" ? "等待复核" : status);
}

function reviewStatusLabel(status: string) {
  return {
    pending: "待确认",
    kept: "保留",
    removed: "移除",
    resolved: "已处理",
    not_needed: "无需复核",
  }[status] ?? status;
}

function reviewStatusTone(status: string) {
  return {
    pending: "bg-amber-400/10 text-amber-300 ring-amber-400/20",
    kept: "bg-emerald-400/10 text-emerald-300 ring-emerald-400/20",
    removed: "bg-rose-400/10 text-rose-300 ring-rose-400/20",
    resolved: "bg-sky-400/10 text-sky-300 ring-sky-400/20",
    not_needed: "bg-white/5 text-[var(--text-secondary)] ring-white/10",
  }[status] ?? "bg-white/5 text-[var(--text-secondary)] ring-white/10";
}

function defaultStageMessage(stage: ImportStage) {
  return {
    parse: "等待开始解析账单文件。",
    dedupe: "等待识别重复交易与入库。",
    duplicate_review: "等待复核跨来源疑似重复交易。",
    classify: "等待规则与 AI 分类。",
    beancount: "等待生成 Beancount 分录。",
  }[stage.stage_key] ?? "等待阶段消息。";
}

function stageTone(status: string) {
  return {
    pending: {
      circle: "border-white/8 bg-[var(--bg-muted)] text-[var(--text-muted)]",
      badge: "bg-white/5 text-[var(--text-secondary)] ring-white/10",
    },
    processing: {
      circle: "border-[var(--gold-400)] bg-[rgba(212,168,67,0.08)] text-[var(--gold-400)] ring-2 ring-[rgba(212,168,67,0.18)]",
      badge: "bg-[rgba(212,168,67,0.1)] text-[var(--gold-400)] ring-[rgba(212,168,67,0.22)]",
    },
    done: {
      circle: "border-[var(--gold-400)] bg-[var(--gold-400)] text-black",
      badge: "bg-emerald-400/10 text-emerald-300 ring-emerald-400/20",
    },
    failed: {
      circle: "border-rose-400/30 bg-rose-400/12 text-rose-300",
      badge: "bg-rose-400/10 text-rose-300 ring-rose-400/20",
    },
  }[status] ?? {
    circle: "border-white/8 bg-[var(--bg-muted)] text-[var(--text-muted)]",
    badge: "bg-white/5 text-[var(--text-secondary)] ring-white/10",
  };
}
