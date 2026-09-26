/** Site-wide constants for the public landing page. */

/** Replace via `NEXT_PUBLIC_GITHUB_URL` at build time. */
export const GITHUB_URL =
  process.env.NEXT_PUBLIC_GITHUB_URL ?? "https://github.com/your-org/orbit";

export const DEMO_COMPANY = "NovaTech Systems";
export const DEMO_PASSWORD = "Orbit123";
export const DEMO_USERS = [
  { email: "admin@novatech.com", role: "Admin" },
  { email: "hr@novatech.com", role: "HR" },
  { email: "eng@novatech.com", role: "Engineering" },
] as const;

export const SECTIONS = [
  { href: "#preview", label: "Product" },
  { href: "#features", label: "Features" },
  { href: "#architecture", label: "Architecture" },
  { href: "#security", label: "Security" },
] as const;
