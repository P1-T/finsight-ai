import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FinSight AI | Research Desk",
  description: "Claude-powered, evidence-grounded research across US market data, news, and web sources.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return <html lang="en"><body>{children}</body></html>;
}
