import { Check, KeyRound, Lock, Minus, ShieldCheck, Eye } from "lucide-react";

import { Reveal } from "./reveal";

const GUARANTEES = [
  {
    icon: KeyRound,
    title: "HTTP-only session cookies",
    body: "JWTs live in an HTTP-only, SameSite cookie — never in localStorage — and can be made Secure in production.",
  },
  {
    icon: Lock,
    title: "Folder-level permissions",
    body: "Every folder carries an allow-list of roles. Admin sees all; HR and Engineering see only what they are granted.",
  },
  {
    icon: Eye,
    title: "Filtered retrieval",
    body: "Access checks run before vector search, so restricted documents never enter a prompt they should not reach.",
  },
  {
    icon: ShieldCheck,
    title: "Isolated conversations + admin analytics",
    body: "Users only see their own chat history; analytics endpoints require the Admin role.",
  },
];

const MATRIX = [
  { folder: "General", admin: true, hr: true, eng: true },
  { folder: "HR", admin: true, hr: true, eng: false },
  { folder: "Engineering", admin: true, hr: false, eng: true },
  { folder: "Product", admin: true, hr: false, eng: true },
  { folder: "Security", admin: true, hr: false, eng: true },
  { folder: "Legal", admin: true, hr: true, eng: false },
];

function Allowed({ allowed }: { allowed: boolean }) {
  return allowed ? (
    <Check className="mx-auto size-4 text-primary" aria-label="allowed" />
  ) : (
    <Minus
      className="mx-auto size-4 text-muted-foreground/40"
      aria-label="not allowed"
    />
  );
}

export function Security() {
  return (
    <section id="security" className="scroll-mt-24 py-16 md:py-24">
      <div className="mx-auto w-full max-w-6xl px-5">
        <div className="grid items-start gap-10 lg:grid-cols-2">
          <Reveal>
            <p className="text-xs font-medium tracking-[0.2em] text-primary uppercase">
              Security &amp; RBAC
            </p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight md:text-4xl">
              Permissions are the product
            </h2>
            <p className="mt-3 text-muted-foreground">
              Orbit ships with three seeded roles and enforces them at every
              layer — from the cookie to the vector store.
            </p>

            <div className="mt-8 grid gap-5 sm:grid-cols-2">
              {GUARANTEES.map((guarantee) => (
                <div key={guarantee.title}>
                  <span className="inline-flex size-9 items-center justify-center rounded-lg bg-primary/15 text-primary">
                    <guarantee.icon className="size-4.5" />
                  </span>
                  <h3 className="mt-3 text-sm font-medium">
                    {guarantee.title}
                  </h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
                    {guarantee.body}
                  </p>
                </div>
              ))}
            </div>
          </Reveal>

          <Reveal delay={120}>
            <div
              data-testid="rbac-matrix"
              className="glass-card overflow-hidden rounded-2xl border border-border/70"
            >
              <div className="border-b border-border/60 px-5 py-4">
                <h3 className="text-sm font-medium">
                  Default access matrix
                </h3>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  Seed role × folder — as enforced in the API
                </p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-xs text-muted-foreground">
                      <th className="px-5 py-3 text-left font-medium">
                        Folder
                      </th>
                      <th className="px-3 py-3 text-center font-medium">
                        Admin
                      </th>
                      <th className="px-3 py-3 text-center font-medium">HR</th>
                      <th className="px-3 py-3 text-center font-medium">
                        Eng
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {MATRIX.map((row) => (
                      <tr key={row.folder} className="border-t border-border/50">
                        <td className="px-5 py-2.5 text-[13px]">
                          {row.folder}
                        </td>
                        <td className="px-3 py-2.5">
                          <Allowed allowed={row.admin} />
                        </td>
                        <td className="px-3 py-2.5">
                          <Allowed allowed={row.hr} />
                        </td>
                        <td className="px-3 py-2.5">
                          <Allowed allowed={row.eng} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="border-t border-border/60 px-5 py-3 text-xs text-muted-foreground">
                Demo tenant: NovaTech Systems · three accounts, five private
                folders, one shared General folder.
              </p>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
