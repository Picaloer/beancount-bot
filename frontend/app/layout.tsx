import type { Metadata } from "next";
import Link from "next/link";
import { Noto_Sans_SC } from "next/font/google";
import "./globals.css";

const notoSansSC = Noto_Sans_SC({
  subsets: ["latin"],
  weight: ["400", "500", "700"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Beancount Bot",
  description: "AI-powered bill management & accounting",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh">
      <body className={`${notoSansSC.className} min-h-screen bg-[radial-gradient(circle_at_top,#fff9ec_0%,#f7f2e8_38%,#efe7da_100%)] text-stone-900 antialiased`}>
        <div className="min-h-screen bg-[linear-gradient(135deg,rgba(255,255,255,0.72),rgba(247,241,231,0.82))]">
          <nav className="sticky top-0 z-10 border-b border-stone-200/70 bg-white/80 px-6 py-4 shadow-[0_8px_30px_rgba(120,98,63,0.08)] backdrop-blur">
            <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-4">
              <Link href="/" className="mr-4 text-lg font-bold tracking-[0.16em] text-amber-800 uppercase">
                Beancount Bot
              </Link>
              <div className="flex flex-wrap gap-5 text-sm font-medium text-stone-600">
                <Link href="/" className="transition-colors hover:text-amber-700">看板</Link>
                <Link href="/import" className="transition-colors hover:text-amber-700">导入账单</Link>
                <Link href="/reports" className="transition-colors hover:text-amber-700">财务报告</Link>
                <Link href="/budgets" className="transition-colors hover:text-amber-700">预算规划</Link>
                <Link href="/transactions" className="transition-colors hover:text-amber-700">交易明细</Link>
                <Link href="/query" className="transition-colors hover:text-amber-700">问答助手</Link>
              </div>
            </div>
          </nav>
          <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
