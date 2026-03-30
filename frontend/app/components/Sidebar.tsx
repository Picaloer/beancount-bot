"use client";

import type { ComponentType, SVGProps } from "react";
import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cx } from "@/app/components/Card";

type IconComponent = ComponentType<SVGProps<SVGSVGElement>>;

type NavItem = {
  href: string;
  icon: IconComponent;
  label: string;
};

const NAV: NavItem[] = [
  { href: "/", label: "看板", icon: DashboardIcon },
  { href: "/import", label: "导入账单", icon: ImportIcon },
  { href: "/reports", label: "财务报告", icon: ReportsIcon },
  { href: "/budgets", label: "预算规划", icon: BudgetIcon },
  { href: "/transactions", label: "交易明细", icon: TransactionsIcon },
  { href: "/query", label: "问答助手", icon: QueryIcon },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const closeMenu = () => setOpen(false);

  useEffect(() => {
    if (!open) {
      return;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open]);

  return (
    <>
      <div className="lg:hidden">
        <div className="fixed inset-x-0 top-0 z-40 flex h-16 items-center justify-between border-b border-[var(--border-default)] bg-[rgba(15,13,10,0.94)] px-4 backdrop-blur-xl">
          <Link href="/" className="flex items-center gap-3" onClick={closeMenu}>
            <BrandGlyph className="h-8 w-8 text-[var(--gold-400)]" />
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Dark Ledger</p>
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[var(--text-primary)]">Beancount</p>
            </div>
          </Link>
          <button
            aria-expanded={open}
            aria-label="打开导航菜单"
            className="flex h-10 w-10 items-center justify-center rounded-2xl border border-[var(--border-default)] bg-[var(--bg-surface)] text-[var(--text-primary)]"
            onClick={() => setOpen(true)}
            type="button"
          >
            <MenuIcon className="h-5 w-5" />
          </button>
        </div>

        <div className={cx("fixed inset-0 z-50 transition-opacity", open ? "pointer-events-auto opacity-100" : "pointer-events-none opacity-0")}>
          <button
            aria-label="关闭导航菜单"
            className="absolute inset-0 bg-black/70"
            onClick={() => setOpen(false)}
            type="button"
          />
          <div className={cx("absolute inset-y-0 left-0 w-60 transition-transform duration-300", open ? "translate-x-0" : "-translate-x-full")}>
            <aside className="flex min-h-screen flex-col border-r border-[var(--border-default)] bg-[var(--bg-base)] shadow-[0_18px_50px_rgba(0,0,0,0.5)]">
              <div className="flex h-16 items-center justify-between px-5">
                <BrandLockup onClick={closeMenu} />
                <button
                  aria-label="关闭导航菜单"
                  className="flex h-10 w-10 items-center justify-center rounded-2xl border border-[var(--border-default)] bg-[var(--bg-surface)] text-[var(--text-primary)]"
                  onClick={() => setOpen(false)}
                  type="button"
                >
                  <CloseIcon className="h-5 w-5" />
                </button>
              </div>
              <SidebarBody pathname={pathname} onNavigate={closeMenu} />
            </aside>
          </div>
        </div>
      </div>

      <div className="hidden w-60 shrink-0 lg:block">
        <aside className="sticky top-0 flex min-h-screen w-60 flex-col border-r border-[var(--border-default)] bg-[var(--bg-base)]">
          <div className="flex h-16 items-center px-5">
            <BrandLockup />
          </div>
          <SidebarBody pathname={pathname} />
        </aside>
      </div>
    </>
  );
}

function SidebarBody({
  onNavigate,
  pathname,
}: {
  onNavigate?: () => void;
  pathname: string;
}) {
  return (
    <>
      <nav className="mt-5 flex-1 space-y-1 px-3">
        {NAV.map((item) => {
          const active = isActivePath(pathname, item.href);
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cx(
                "flex h-11 items-center gap-3 rounded-r-xl border-l-2 pl-5 pr-4 text-sm font-medium transition-all",
                active
                  ? "border-[var(--gold-400)] bg-[var(--bg-surface)] text-[var(--gold-400)] shadow-[inset_0_0_0_1px_rgba(212,168,67,0.08)]"
                  : "border-transparent text-[var(--text-secondary)] hover:bg-[var(--bg-surface)] hover:text-[var(--text-primary)]"
              )}
              onClick={onNavigate}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="px-5 pb-5">
        <div className="rounded-[24px] border border-[var(--border-subtle)] bg-[rgba(26,22,16,0.9)] p-4">
          <p className="text-[11px] uppercase tracking-[0.24em] text-[var(--text-muted)]">Ledger Mode</p>
          <p className="mt-3 text-sm leading-7 text-[var(--text-secondary)]">
            把导入、分类、预算和月报都收进同一册暗金账本里。
          </p>
        </div>
      </div>
    </>
  );
}

function BrandLockup({ onClick }: { onClick?: () => void }) {
  return (
    <Link href="/" className="flex items-center gap-4" onClick={onClick}>
      <span className="h-10 w-1 rounded-full bg-[var(--gold-400)] shadow-[0_0_24px_rgba(212,168,67,0.35)]" />
      <div>
        <p className="text-[11px] uppercase tracking-[0.24em] text-[var(--text-muted)]">Dark Ledger</p>
        <p className="text-base font-bold uppercase tracking-[0.18em] text-[var(--text-primary)]">Beancount</p>
        <p className="text-xs text-[var(--text-muted)]">Gold Edition</p>
      </div>
    </Link>
  );
}

function isActivePath(pathname: string, href: string) {
  if (href === "/") {
    return pathname === "/";
  }

  return pathname === href || pathname.startsWith(`${href}/`);
}

function BrandGlyph(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
      <rect x="4" y="3" width="16" height="18" rx="4" stroke="currentColor" strokeWidth="1.6" />
      <path d="M8 8H16" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M8 12H14" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M8 16H12" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

function DashboardIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
      <path d="M4 13.5L12 5L20 13.5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M7 11.5V19H17V11.5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ImportIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
      <path d="M12 4V14" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      <path d="M8.5 10.5L12 14L15.5 10.5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M5 18.5H19" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}

function ReportsIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
      <path d="M5 18.5V10.5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      <path d="M12 18.5V6.5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      <path d="M19 18.5V13" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}

function BudgetIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
      <rect x="4" y="6" width="16" height="12" rx="3" stroke="currentColor" strokeWidth="1.7" />
      <path d="M15 12H15.01" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
      <path d="M4 10H20" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}

function TransactionsIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
      <path d="M6 7H18" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      <path d="M6 12H18" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      <path d="M6 17H13" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}

function QueryIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
      <path d="M7.5 16.5L5 19V6.5C5 5.67 5.67 5 6.5 5H17.5C18.33 5 19 5.67 19 6.5V15.5C19 16.33 18.33 17 17.5 17H9" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M9 9.25H15" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      <path d="M9 12.75H13.5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}

function MenuIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
      <path d="M5 7H19" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M5 12H19" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M5 17H19" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function CloseIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
      <path d="M7 7L17 17" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M17 7L7 17" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}
