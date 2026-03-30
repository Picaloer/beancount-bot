import type { Metadata } from "next";

import Sidebar from "@/app/components/Sidebar";
import "./globals.css";

export const metadata: Metadata = {
  title: "Beancount Bot",
  description: "AI-powered bill management and accounting ledger",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh">
      <body className="bg-[var(--bg-base)] text-[var(--text-primary)] antialiased">
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="min-w-0 flex-1 px-4 pb-6 pt-24 sm:px-6 sm:pb-8 lg:p-8">
            <div className="mx-auto w-full max-w-[1440px]">{children}</div>
          </main>
        </div>
      </body>
    </html>
  );
}
