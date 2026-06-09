import type { Metadata } from "next";
import Sidebar from "@/components/layout/Sidebar";
import AIChat from "@/components/chat/AIChat";
import "./globals.css";

export const metadata: Metadata = {
  title: "MakeNovel - LLM 辅助写小说",
  description: "基于大语言模型的长篇小说创作工具",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" className="h-full antialiased">
      <body className="min-h-full flex bg-zinc-50 dark:bg-zinc-950">
        <Sidebar />
        <main className="flex-1 overflow-auto">
          {children}
        </main>
        <AIChat />
      </body>
    </html>
  );
}
