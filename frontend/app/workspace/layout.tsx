import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Workspace — Orbit",
  description: "Ask questions across your Orbit knowledge base",
};

export default function WorkspaceLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="flex h-screen flex-col overflow-hidden">{children}</div>
  );
}
