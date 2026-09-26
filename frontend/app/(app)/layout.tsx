import { AppShell } from "@/components/app-shell/app-shell";

export default function AuthedLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return <AppShell>{children}</AppShell>;
}
