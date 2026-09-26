import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Knowledge Base",
  description: "Upload, organise and search documents in Orbit",
};

export default function KnowledgeLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return children;
}
