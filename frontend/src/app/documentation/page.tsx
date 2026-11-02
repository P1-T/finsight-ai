import type { Metadata } from "next";
import { DocumentationPage } from "@/components/chat/DocumentationPage";

export const metadata: Metadata = {
  title: "Finsight AI | Documentation",
  description: "How Finsight AI plans research, gathers context, and renders structured responses.",
};

export default function DocumentationRoute() {
  return <DocumentationPage />;
}
