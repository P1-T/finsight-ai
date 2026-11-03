import type { Metadata } from "next";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import "./globals.css";

export const metadata: Metadata = {
  title: "Finsight AI | Research Desk",
  description: "Claude-powered, evidence-grounded research across US market data, news, and web sources.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return <html lang="en" data-theme="dark"><body>{children}<ThemeToggle /></body></html>;
}
