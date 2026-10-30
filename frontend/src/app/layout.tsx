import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FinSight AI | Market Research",
  description: "AI-powered market and company research dashboard.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return <html lang="en"><body>{children}</body></html>;
}
