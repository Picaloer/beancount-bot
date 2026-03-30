"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import useSWR from "swr";
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
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-stone-900">交易明细</h1>
          <p className="mt-1 text-sm text-stone-500">手动修正分类，并把高频判断沉淀为规则，减少下次导入的人工操作。</p>
        </div>
        {data && <p className="text-sm text-stone-500">共 {data.total} 条</p>}
      </div>

      {notice && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          {notice}
        </div>
      )}

      {error && (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <section className="space-y-6">
          <div className="rounded-3xl border border-stone-200 bg-white/90 p-4 shadow-[0_18px_40px_rgba(84,62,34,0.06)]">
            <div className="flex flex-wrap gap-3">
              <input
                type="month"
                value={yearMonth}
                onChange={(e) => {
                  setYearMonth(e.target.value);
                  setPage(1);
                }}
                className="rounded-xl border border-stone-300 px-3 py-2 text-sm focus:border-amber-500 focus:outline-none"
              />
              <select
                value={categoryL1}
                onChange={(e) => {
                  setCategoryL1(e.target.value);
                  setPage(1);
                }}
                className="rounded-xl border border-stone-300 px-3 py-2 text-sm focus:border-amber-500 focus:outline-none"
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
                className="rounded-xl border border-stone-300 px-3 py-2 text-sm focus:border-amber-500 focus:outline-none"
              >
                {DIRECTIONS.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
              {(yearMonth || categoryL1 || direction) && (
                <button
                  type="button"
                  onClick={() => {
                    setYearMonth("");
                    setCategoryL1("");
                    setDirection("");
                    setPage(1);
                  }}
                  className="text-sm text-stone-400 transition-colors hover:text-stone-600"
                >
                  清除筛选
                </button>
              )}
            </div>
          </div>

          <div className="overflow-hidden rounded-3xl border border-stone-200 bg-white/90 shadow-[0_18px_40px_rgba(84,62,34,0.06)]">
            {isLoading ? (
              <div className="py-20 text-center text-stone-400">加载中...</div>
            ) : !data || data.items.length === 0 ? (
              <div className="py-20 text-center text-stone-400">
                <p className="mb-2 text-3xl">🔍</p>
                <p>
                  暂无数据，请先
                  <Link href="/import" className="text-amber-700 hover:underline">
                    导入账单
                  </Link>
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="bg-stone-50 text-xs uppercase tracking-wide text-stone-500">
                    <tr>
                      <th className="px-4 py-3 text-left">时间</th>
                      <th className="px-4 py-3 text-left">商家</th>
                      <th className="px-4 py-3 text-left">描述</th>
                      <th className="px-4 py-3 text-left">分类</th>
                      <th className="px-4 py-3 text-right">金额</th>
                      <th className="px-4 py-3 text-center">操作</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-stone-100">
                    {data.items.map((tx) => {
                      const isEditing = editingId === tx.id;
                      const isSaving = savingId === tx.id;
                      const canRemember = Boolean(tx.merchant || tx.description);

                      return (
                        <tr key={tx.id} className="hover:bg-amber-50/40">
                          <td className="whitespace-nowrap px-4 py-3 text-stone-500">
                            {new Date(tx.transaction_at).toLocaleDateString("zh-CN", {
                              month: "2-digit",
                              day: "2-digit",
                            })}
                          </td>
                          <td className="max-w-[160px] truncate px-4 py-3 font-medium text-stone-800">
                            {tx.merchant || "—"}
                          </td>
                          <td className="max-w-[220px] truncate px-4 py-3 text-stone-500">
                            {tx.description || "—"}
                          </td>
                          <td className="px-4 py-3 align-top">
                            {isEditing ? (
                              <div className="flex min-w-[220px] gap-2">
                                <select
                                  value={editL1}
                                  onChange={(e) => {
                                    setEditL1(e.target.value);
                                    setEditL2("");
                                  }}
                                  className="rounded-lg border border-stone-300 px-2 py-1 text-xs focus:border-amber-500 focus:outline-none"
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
                                  className="rounded-lg border border-stone-300 px-2 py-1 text-xs focus:border-amber-500 focus:outline-none"
                                >
                                  <option value="">—</option>
                                  {subCategories.map((subCategory) => (
                                    <option key={subCategory} value={subCategory}>
                                      {subCategory}
                                    </option>
                                  ))}
                                </select>
                              </div>
                            ) : (
                              <CategoryTag tx={tx} />
                            )}
                          </td>
                          <td
                            className={`px-4 py-3 text-right font-medium ${
                              tx.direction === "income"
                                ? "text-emerald-600"
                                : tx.direction === "expense"
                                  ? "text-rose-600"
                                  : "text-stone-600"
                            }`}
                          >
                            {tx.direction === "income" ? "+" : tx.direction === "expense" ? "-" : ""}
                            ¥{tx.amount.toFixed(2)}
                          </td>
                          <td className="px-4 py-3 text-center">
                            {isEditing ? (
                              <div className="flex flex-col items-center gap-1 text-xs sm:flex-row sm:justify-center">
                                <button
                                  type="button"
                                  onClick={() => void saveCategory(tx)}
                                  disabled={isSaving}
                                  className="text-amber-700 transition-colors hover:text-amber-800 disabled:opacity-50"
                                >
                                  {isSaving ? "保存中..." : "保存"}
                                </button>
                                <button
                                  type="button"
                                  onClick={() => void saveCategory(tx, true)}
                                  disabled={isSaving || !canRemember}
                                  className="text-stone-500 transition-colors hover:text-stone-700 disabled:opacity-50"
                                >
                                  保存并记住
                                </button>
                                <button
                                  type="button"
                                  onClick={() => prefillRule(tx)}
                                  disabled={!canRemember}
                                  className="text-stone-400 transition-colors hover:text-stone-600 disabled:opacity-50"
                                >
                                  填入规则表单
                                </button>
                                <button
                                  type="button"
                                  onClick={() => setEditingId(null)}
                                  className="text-stone-400 transition-colors hover:text-stone-600"
                                >
                                  取消
                                </button>
                              </div>
                            ) : (
                              <button
                                type="button"
                                onClick={() => beginEdit(tx)}
                                className="text-xs text-stone-500 transition-colors hover:text-amber-700"
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
          </div>

          {totalPages > 1 && (
            <div className="flex justify-center gap-2">
              <button
                type="button"
                onClick={() => setPage((current) => Math.max(1, current - 1))}
                disabled={page === 1}
                className="rounded-xl border border-stone-300 px-3 py-1.5 text-sm text-stone-700 transition-colors hover:border-amber-400 disabled:opacity-40"
              >
                上一页
              </button>
              <span className="px-3 py-1.5 text-sm text-stone-500">
                {page} / {totalPages}
              </span>
              <button
                type="button"
                onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
                disabled={page === totalPages}
                className="rounded-xl border border-stone-300 px-3 py-1.5 text-sm text-stone-700 transition-colors hover:border-amber-400 disabled:opacity-40"
              >
                下一页
              </button>
            </div>
          )}
        </section>

        <aside className="space-y-6 xl:sticky xl:top-24 xl:self-start">
          <section className="rounded-3xl border border-stone-200 bg-white/90 p-5 shadow-[0_18px_40px_rgba(84,62,34,0.06)]">
            <div className="mb-4">
              <h2 className="text-lg font-semibold text-stone-900">新增规则</h2>
              <p className="mt-1 text-sm text-stone-500">把常见商家或描述保存为规则，后续导入会优先自动分类。</p>
            </div>

            <form className="space-y-3" onSubmit={handleCreateRule}>
              <label className="block space-y-1">
                <span className="text-xs font-medium uppercase tracking-wide text-stone-500">匹配字段</span>
                <select
                  value={ruleMatchField}
                  onChange={(e) => setRuleMatchField(e.target.value as "merchant" | "description" | "any")}
                  className="w-full rounded-xl border border-stone-300 px-3 py-2 text-sm focus:border-amber-500 focus:outline-none"
                >
                  {RULE_MATCH_FIELDS.map((field) => (
                    <option key={field.value} value={field.value}>
                      {field.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block space-y-1">
                <span className="text-xs font-medium uppercase tracking-wide text-stone-500">关键词</span>
                <input
                  value={ruleMatchValue}
                  onChange={(e) => setRuleMatchValue(e.target.value)}
                  placeholder="例如：南京大牌档"
                  className="w-full rounded-xl border border-stone-300 px-3 py-2 text-sm focus:border-amber-500 focus:outline-none"
                />
              </label>

              <div className="grid grid-cols-2 gap-3">
                <label className="block space-y-1">
                  <span className="text-xs font-medium uppercase tracking-wide text-stone-500">一级分类</span>
                  <select
                    value={ruleCategoryL1}
                    onChange={(e) => {
                      setRuleCategoryL1(e.target.value);
                      setRuleCategoryL2("");
                    }}
                    className="w-full rounded-xl border border-stone-300 px-3 py-2 text-sm focus:border-amber-500 focus:outline-none"
                  >
                    <option value="">选择分类</option>
                    {categories.map((category) => (
                      <option key={category} value={category}>
                        {category}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block space-y-1">
                  <span className="text-xs font-medium uppercase tracking-wide text-stone-500">二级分类</span>
                  <select
                    value={ruleCategoryL2}
                    onChange={(e) => setRuleCategoryL2(e.target.value)}
                    className="w-full rounded-xl border border-stone-300 px-3 py-2 text-sm focus:border-amber-500 focus:outline-none"
                    disabled={!ruleCategoryL1}
                  >
                    <option value="">—</option>
                    {ruleSubCategories.map((subCategory) => (
                      <option key={subCategory} value={subCategory}>
                        {subCategory}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <button
                type="submit"
                disabled={submittingRule}
                className="w-full rounded-xl bg-amber-700 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-amber-800 disabled:opacity-60"
              >
                {submittingRule ? "保存中..." : "保存规则"}
              </button>
            </form>
          </section>

          <section className="rounded-3xl border border-stone-200 bg-white/90 p-5 shadow-[0_18px_40px_rgba(84,62,34,0.06)]">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-stone-900">已保存规则</h2>
                <p className="mt-1 text-sm text-stone-500">优先级更高的规则会先命中。</p>
              </div>
              <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-800">
                {sortedRules.length} 条
              </span>
            </div>

            <div className="space-y-3">
              {sortedRules.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-stone-200 px-4 py-6 text-center text-sm text-stone-400">
                  还没有自定义规则
                </div>
              ) : (
                sortedRules.map((rule) => (
                  <div key={rule.id} className="rounded-2xl border border-stone-200 bg-stone-50/70 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate font-medium text-stone-800">{rule.match_value}</p>
                        <p className="mt-1 text-xs text-stone-500">
                          {matchFieldLabel(rule.match_field)} · 优先级 {rule.priority}
                        </p>
                        <p className="mt-2 text-sm text-stone-600">
                          {rule.category_l1}
                          {rule.category_l2 ? ` / ${rule.category_l2}` : ""}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => void handleDeleteRule(rule)}
                        disabled={deletingRuleId === rule.id}
                        className="text-xs text-red-500 transition-colors hover:text-red-600 disabled:opacity-50"
                      >
                        {deletingRuleId === rule.id ? "删除中..." : "删除"}
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}

function CategoryTag({ tx }: { tx: Transaction }) {
  const sourceColors: Record<string, string> = {
    user_rule: "bg-emerald-100 text-emerald-700",
    system_rule: "bg-sky-100 text-sky-700",
    llm: "bg-amber-100 text-amber-800",
    manual: "bg-orange-100 text-orange-700",
    fallback: "bg-stone-100 text-stone-500",
  };
  const cls = sourceColors[tx.category_source] ?? "bg-stone-100 text-stone-500";
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs ${cls}`}>
      {tx.category_l1}
      {tx.category_l2 ? ` · ${tx.category_l2}` : ""}
    </span>
  );
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
