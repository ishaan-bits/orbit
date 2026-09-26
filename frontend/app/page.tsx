import { Architecture } from "@/components/landing/architecture";
import { FinalCTA } from "@/components/landing/cta";
import { Features } from "@/components/landing/features";
import { SiteFooter } from "@/components/landing/footer";
import { Hero } from "@/components/landing/hero";
import { Navbar } from "@/components/landing/navbar";
import { ProductPreview } from "@/components/landing/product-preview";
import { Security } from "@/components/landing/security";

export default function HomePage() {
  return (
    <div className="relative min-h-screen overflow-x-clip">
      <Navbar />
      <main>
        <Hero />
        <ProductPreview />
        <Features />
        <Architecture />
        <Security />
        <FinalCTA />
      </main>
      <SiteFooter />
    </div>
  );
}
