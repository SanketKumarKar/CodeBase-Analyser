import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "Codebase Intelligence Agent",
  description:
    "Hybrid-RAG system for natural-language code analysis — semantic search, graph traversal, and persistent conversational memory.",
  keywords: ["code analysis", "AI", "RAG", "developer tools"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} font-sans antialiased bg-[#0a0a0f] text-slate-100`}>
        {children}
      </body>
    </html>
  );
}
