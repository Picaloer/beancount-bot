"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import useSWR from "swr";

import { CategoryTag } from "@/app/components/Badge";
import Card, { cx } from "@/app/components/Card";
import EmptyState from "@/app/components/EmptyState";
import PageHeader from "@/app/components/PageHeader";
import {
  createRule,
  deleteRule,
  getCategoryTree,
  listRules,
  listTransactions,
  type CategoryRule,
  type Transaction,
  updateCategory,
} from "@/lib/api";

const DIRECTIONS = [
  { value: "", label: "全部" },
  { value: "expense", label: "支出" },
  { value: "income", label: "收入" },
  { value: "transfer", label: "转账" },
];

const RULE_MATCH_FIELDS = [
  { value: "merchant", label: "商家" },
  { value: "description", label: "描述" },
  { value: "any", label: "商家或描述" },
] as const;

const inputClassName =
  "rounded-xl border border-[rgba(212,168,67,0.2)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none transition focus:border-[var(--gold-400)]";

const buttonClassName =
  "inline-flex items-center justify-center rounded-xl border border-[rgba(212,168,67,0.22)] bg-[var(--bg-surface)] px-4 py-2 text-sm font-medium text-[var(--text-secondary)] transition hover:border-[var(--gold-400)] hover:text-[var(--text-primary)] disabled:cursor-not-allowed disabled:opacity-50";

const primaryButtonClassName =
  "inline-flex items-center justify-center rounded-xl bg-[var(--gold-400)] px-4 py-2 text-sm font-medium text-black transition hover:bg-[var(--gold-500)] disabled:cursor-not-allowed disabled:opacity-60";

export default function TransactionsPage() {
  const [yearMonth, setYearMonth] = useState("");
  const [categoryL1, setCategoryL1] = useState("");
  const [direction, setDirection] = useState("");
  const [page, setPage] = useState(1);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading, mutate } = useSWR(
    ["transactions", yearMonth, categoryL1, direction, page],
    () =>
      listTransactions({
        year_month: yearMonth || undefined,
        category_l1: categoryL1 || undefined,
        direction: direction || undefined,
        page,
        page_size: 50,
      })
  );

  const { data: catTree } = useSWR("categories", getCategoryTree);
  const { data: rules = [], mutate: mutateRules } = useSWR("rules", listRules);
  const categories = catTree?.tree?.map((category) => category.category_l1) ?? [];

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editL1, setEditL1] = useState("");
  const [editL2, setEditL2] = useState("");
  const [savingId, setSavingId] = useState<string | null>(null);

  const [ruleMatchField, setRuleMatchField] = useState<"merchant" | "description" | "any">("merchant");
  const [ruleMatchValue, setRuleMatchValue] = useState("");
  const [ruleCategoryL1, setRuleCategoryL1] = useState("");
  const [ruleCategoryL2, setRuleCategoryL2] = useState("");
  const [submittingRule, setSubmittingRule] = useState(false);
  const [deletingRuleId, setDeletingRuleId] = useState<string | null>(null);

  const subCategories =
    catTree?.tree?.find((category) => category.category_l1 === editL1)?.subcategories ?? [];
  const ruleSubCategories =
    catTree?.tree?.find((category) => category.category_l1 === ruleCategoryL1)?.subcategories ?? [];

  const totalPages = data ? Math.ceil(data.total / 50) : 1;

  const sortedRules = useMemo(
    () => [...rules].sort((left, right) => right.priority - left.priority),
    [rules]
  );

  function resetMessages() {
    setNotice(null);
    setError(null);
  }

  function resetRuleForm() {
    setRuleMatchField("merchant");
    setRuleMatchValue("");
    setRuleCategoryL1("");
    setRuleCategoryL2("");
  }

  function beginEdit(tx: Transaction) {
    resetMessages();
    setEditingId(tx.id);
    setEditL1(tx.category_l1);
    setEditL2(tx.category_l2 ?? "");
  }

  async function saveCategory(tx: Transaction, rememberRule = false) {
    resetMessages();
    setSavingId(tx.id);

    try {
      await updateCategory(tx.id, editL1, editL2 || null);

      if (rememberRule) {
        const { matchField, matchValue } = preferredRuleSource(tx);
        if (!matchValue) {
          throw new Error("该交易缺少可用于记忆规则的商家或描述");
        }

        await createRule({
          match_value: matchValue,
          match_field: matchField,
          category_l1: editL1,
          category_l2: editL2 || undefined,
          priority: 20,
        });
        await mutateRules();
        setNotice(`已更新分类，并记住规则：${matchValue}`);
      } else {
        setNotice("分类已更新");
      }

      setEditingId(null);
      await mutate();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSavingId(null);
    }
  }

  async function handleCreateRule(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    resetMessages();
    setSubmittingRule(true);

    try {
      await createRule({
        match_value: ruleMatchValue,
        match_field: ruleMatchField,
        category_l1: ruleCategoryL1,
        category_l2: ruleCategoryL2 || undefined,
        priority: 20,
      });
      resetRuleForm();
      await mutateRules();
      setNotice("新规则已保存，后续导入会优先命中这条规则");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "创建规则失败");
    } finally {
      setSubmittingRule(false);
    }
  }

  async function handleDeleteRule(rule: CategoryRule) {
    resetMessages();
    setDeletingRuleId(rule.id);

    try {
      await deleteRule(rule.id);
      await mutateRules();
      setNotice(`已删除规则：${rule.match_value}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "删除规则失败");
    } finally {
      setDeletingRuleId(null);
    }
  }

  function prefillRule(tx: Transaction) {
    const { matchField, matchValue } = preferredRuleSource(tx);
    if (!matchValue) {
      setError("该交易缺少可用于记忆规则的商家或描述");
      return;
    }

    resetMessages();
    setRuleMatchField(matchField);
    setRuleMatchValue(matchValue);
    setRuleCategoryL1(editingId === tx.id ? editL1 : tx.category_l1);
    setRuleCategoryL2(editingId === tx.id ? editL2 : tx.category_l2 ?? "");
    setNotice("已将当前交易填入规则表单，可直接保存");
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Transaction Ledger"
        title="交易明细"
        description="在暗色账册里逐笔修正分类，把高频判断沉淀成规则，让下一次导入更接近零人工。"
      >
        {data ? (
          <div className="rounded-xl border border-[rgba(212,168,67,0.2)] bg-[rgba(255,255,255,0.03)] px-4 py-2 text-sm text-[var(--text-secondary)]">
            共 <span className="tabular text-[var(--text-primary)]">{data.total}</span> 条
          </div>
        ) : null}
      </PageHeader>

      {notice ? <MessageCard tone="notice">{notice}</MessageCard> : null}
      {error ? <MessageCard tone="error">{error}</MessageCard> : null}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <section className="space-y-6">
          <Card variant="surface" className="p-4">
            <div className="flex flex-wrap gap-3">
              <input
                type="month"
                value={yearMonth}
                onChange={(e) => {
                  setYearMonth(e.target.value);
                  setPage(1);
                }}
                className={inputClassName}
              />
              <select
                value={categoryL1}
                onChange={(e) => {
                  setCategoryL1(e.target.value);
                  setPage(1);
                }}
                className={inputClassName}
              >
                <option value="">全部分类</option>
                {categories.map((category) => (
                  <option key={category} value={category}>
                    {category}
                  </option>
                ))}
              </select>
              <select
                value={direction}
                onChange={(e) => {
                  setDirection(e.target.value);
                  setPage(1);
                }}
                className={inputClassName}
              >
                {DIRECTIONS.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
              {(yearMonth || categoryL1 || direction) ? (
                <button
                  type="button"
                  onClick={() => {
                    setYearMonth("");
                    setCategoryL1("");
                    setDirection("");
                    setPage(1);
                  }}
                  className={buttonClassName}
                >
                  清除筛选
                </button>
              ) : null}
            </div>
          </Card>

          <Card variant="surface" className="overflow-hidden">
            {isLoading ? (
              <div className="py-20 text-center text-sm text-[var(--text-muted)]">正在装订交易账页...</div>
            ) : !data || data.items.length === 0 ? (
              <div className="p-6">
                <EmptyState
                  title="还没有交易数据"
                  description="先导入账单后，这里会按暗色账册表格展示所有流水，并支持逐笔修正分类。"
                  action={
                    <Link href="/import" className={primaryButtonClassName}>
                      去导入账单
                    </Link>
                  }
                />
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="bg-[var(--bg-elevated)] text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">
                    <tr>
                      <th className="px-4 py-4 text-left">时间</th>
                      <th className="px-4 py-4 text-left">商家</th>
                      <th className="px-4 py-4 text-left">描述</th>
                      <th className="px-4 py-4 text-left">分类</th>
                      <th className="px-4 py-4 text-right">金额</th>
                      <th className="px-4 py-4 text-center">操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.items.map((tx, index) => {
                      const isEditing = editingId === tx.id;
                      const isSaving = savingId === tx.id;
                      const canRemember = Boolean(tx.merchant || tx.description);

                      return (
                        <tr
                          key={tx.id}
                          className={cx(
                            "border-t border-white/6 transition-colors hover:bg-[var(--bg-elevated)]",
                            index % 2 === 0 ? "bg-[rgba(20,15,11,0.5)]" : "bg-transparent"
                          )}
                        >
                          <td className="whitespace-nowrap px-4 py-4 text-[var(--text-secondary)]">
                            {new Date(tx.transaction_at).toLocaleDateString("zh-CN", {
                              month: "2-digit",
                              day: "2-digit",
                              timeZone: "Asia/Shanghai",
                            })}
                          </td>
                          <td className="max-w-[170px] truncate px-4 py-4 font-medium text-[var(--text-primary)]">
                            {tx.merchant || "-"}
                          </td>
                          <td className="max-w-[240px] truncate px-4 py-4 text-[var(--text-secondary)]">
                            {tx.description || "-"}
                          </td>
                          <td className="px-4 py-4 align-top">
                            {isEditing ? (
                              <div className="flex min-w-[240px] gap-2">
                                <select
                                  value={editL1}
                                  onChange={(e) => {
                                    setEditL1(e.target.value);
                                    setEditL2("");
                                  }}
                                  className={cx(inputClassName, "px-2 py-1.5 text-xs")}
                                >
                                  {categories.map((category) => (
                                    <option key={category} value={category}>
                                      {category}
                                    </option>
                                  ))}
                                </select>
                                <select
                                  value={editL2}
                                  onChange={(e) => setEditL2(e.target.value)}
                                  className={cx(inputClassName, "px-2 py-1.5 text-xs")}
                                >
                                  <option value="">-</option>
                                  {subCategories.map((subCategory) => (
                                    <option key={subCategory} value={subCategory}>
                                      {subCategory}
                                    </option>
                                  ))}
                                </select>
                              </div>
                            ) : (
                              <CategoryTag
                                categoryL1={tx.category_l1}
                                categoryL2={tx.category_l2}
                                source={tx.category_source}
                              />
                            )}
                          </td>
                          <td
                            className={cx(
                              "tabular px-4 py-4 text-right font-semibold",
                              tx.direction === "income"
                                ? "text-emerald-300"
                                : tx.direction === "expense"
                                  ? "text-rose-300"
                                  : "text-[var(--text-secondary)]"
                            )}
                          >
                            {tx.direction === "income" ? "+" : tx.direction === "expense" ? "-" : ""}
                            ¥{tx.amount.toFixed(2)}
                          </td>
                          <td className="px-4 py-4 text-center">
                            {isEditing ? (
                              <div className="flex flex-col items-center gap-1 text-xs sm:flex-row sm:justify-center">
                                <button
                                  type="button"
                                  onClick={() => void saveCategory(tx)}
                                  disabled={isSaving}
                                  className="text-[var(--gold-400)] transition hover:text-[var(--text-primary)] disabled:opacity-50"
                                >
                                  {isSaving ? "保存中..." : "保存"}
                                </button>
                                <button
                                  type="button"
                                  onClick={() => void saveCategory(tx, true)}
                                  disabled={isSaving || !canRemember}
                                  className="text-[var(--text-secondary)] transition hover:text-[var(--text-primary)] disabled:opacity-50"
                                >
                                  保存并记住
                                </button>
                                <button
                                  type="button"
                                  onClick={() => prefillRule(tx)}
                                  disabled={!canRemember}
                                  className="text-[var(--text-muted)] transition hover:text-[var(--text-secondary)] disabled:opacity-50"
                                >
                                  填入规则表单
                                </button>
                                <button
                                  type="button"
                                  onClick={() => setEditingId(null)}
                                  className="text-[var(--text-muted)] transition hover:text-[var(--text-secondary)]"
                                >
                                  取消
                                </button>
                              </div>
                            ) : (
                              <button
                                type="button"
                                onClick={() => beginEdit(tx)}
                                className="text-xs text-[var(--text-secondary)] transition hover:text-[var(--gold-400)]"
                              >
                                编辑
                              </button>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          {totalPages > 1 ? (
            <div className="flex items-center justify-center gap-2">
              <button
                type="button"
                onClick={() => setPage((current) => Math.max(1, current - 1))}
                disabled={page === 1}
                className={buttonClassName}
              >
                上一页
              </button>
              <span className="tabular px-3 py-1.5 text-sm text-[var(--gold-400)]">
                {page} / {totalPages}
              </span>
              <button
                type="button"
                onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
                disabled={page === totalPages}
                className={buttonClassName}
              >
                下一页
              </button>
            </div>
          ) : null}
        </section>

        <aside className="space-y-6 xl:sticky xl:top-8 xl:self-start">
          <Card variant="surface" className="p-5">
            <div className="mb-4">
              <h2 className="text-lg font-semibold text-[var(--text-primary)]">新增规则</h2>
              <p className="mt-1 text-sm leading-7 text-[var(--text-secondary)]">
                把常见商家或描述保存成规则，后续导入会优先自动分类。
              </p>
            </div>

            <form className="space-y-3" onSubmit={handleCreateRule}>
              <label className="block space-y-1.5">
                <span className="text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">匹配字段</span>
                <select
                  value={ruleMatchField}
                  onChange={(e) => setRuleMatchField(e.target.value as "merchant" | "description" | "any")}
                  className={cx(inputClassName, "w-full")}
                >
                  {RULE_MATCH_FIELDS.map((field) => (
                    <option key={field.value} value={field.value}>
                      {field.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block space-y-1.5">
                <span className="text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">关键词</span>
                <input
                  value={ruleMatchValue}
                  onChange={(e) => setRuleMatchValue(e.target.value)}
                  placeholder="例如：南京大牌档"
                  className={cx(inputClassName, "w-full")}
                />
              </label>

              <div className="grid grid-cols-2 gap-3">
                <label className="block space-y-1.5">
                  <span className="text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">一级分类</span>
                  <select
                    value={ruleCategoryL1}
                    onChange={(e) => {
                      setRuleCategoryL1(e.target.value);
                      setRuleCategoryL2("");
                    }}
                    className={cx(inputClassName, "w-full")}
                  >
                    <option value="">选择分类</option>
                    {categories.map((category) => (
                      <option key={category} value={category}>
                        {category}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block space-y-1.5">
                  <span className="text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">二级分类</span>
                  <select
                    value={ruleCategoryL2}
                    onChange={(e) => setRuleCategoryL2(e.target.value)}
                    className={cx(inputClassName, "w-full")}
                    disabled={!ruleCategoryL1}
                  >
                    <option value="">-</option>
                    {ruleSubCategories.map((subCategory) => (
                      <option key={subCategory} value={subCategory}>
                        {subCategory}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <button type="submit" disabled={submittingRule} className={cx(primaryButtonClassName, "w-full")}>
                {submittingRule ? "保存中..." : "保存规则"}
              </button>
            </form>
          </Card>

          <Card variant="surface" className="p-5">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-[var(--text-primary)]">已保存规则</h2>
                <p className="mt-1 text-sm text-[var(--text-secondary)]">优先级更高的规则会先命中。</p>
              </div>
              <span className="rounded-full bg-[rgba(212,168,67,0.12)] px-3 py-1 text-xs font-medium text-[var(--gold-400)]">
                {sortedRules.length} 条
              </span>
            </div>

            <div className="space-y-3">
              {sortedRules.length === 0 ? (
                <EmptyState
                  className="p-6"
                  title="还没有规则"
                  description="从交易里保存第一条规则后，这里会按优先级展示所有规则。"
                />
              ) : (
                sortedRules.map((rule) => (
                  <div key={rule.id} className="rounded-[22px] border border-[var(--border-subtle)] bg-[var(--bg-elevated)] p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate font-medium text-[var(--gold-400)]">{rule.match_value}</p>
                        <p className="mt-1 text-xs text-[var(--text-muted)]">
                          {matchFieldLabel(rule.match_field)} / 优先级 {rule.priority}
                        </p>
                        <p className="mt-2 text-sm text-[var(--text-secondary)]">
                          {rule.category_l1}
                          {rule.category_l2 ? ` / ${rule.category_l2}` : ""}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => void handleDeleteRule(rule)}
                        disabled={deletingRuleId === rule.id}
                        className="text-xs text-rose-300 transition hover:text-rose-200 disabled:opacity-50"
                      >
                        {deletingRuleId === rule.id ? "删除中..." : "删除"}
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </Card>
        </aside>
      </div>
    </div>
  );
}

function MessageCard({
  children,
  tone,
}: {
  children: React.ReactNode;
  tone: "error" | "notice";
}) {
  const toneClassName =
    tone === "error"
      ? "border-rose-400/20 bg-rose-400/8 text-rose-200"
      : "border-emerald-400/20 bg-emerald-400/8 text-emerald-200";

  return <div className={cx("rounded-[24px] border px-4 py-3 text-sm", toneClassName)}>{children}</div>;
}

function preferredRuleSource(tx: Transaction) {
  if (tx.merchant) {
    return { matchField: "merchant" as const, matchValue: tx.merchant };
  }
  if (tx.description) {
    return { matchField: "description" as const, matchValue: tx.description };
  }
  return { matchField: "merchant" as const, matchValue: "" };
}

function matchFieldLabel(field: CategoryRule["match_field"]) {
  if (field === "merchant") {
    return "匹配商家";
  }
  if (field === "description") {
    return "匹配描述";
  }
  return "匹配商家或描述";
}
