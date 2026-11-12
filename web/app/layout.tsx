import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";

import { SiteFooter, SiteHeader } from "@/components/shell/site-chrome";
import { TooltipProvider } from "@/components/ui/tooltip";

import "./globals.css";

const inter = Inter({ variable: "--font-sans", subsets: ["latin"] });
const jetbrainsMono = JetBrains_Mono({ variable: "--font-jetbrains-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: { default: "FairValue Football", template: "%s · FairValue Football" },
  description:
    "Transfer-market intelligence: how market values and fees compare with measurable performance, with the uncertainty shown.",
};

// Runs before first paint: dark by default, light only if the visitor chose it. Avoids a theme flash.
const THEME_SCRIPT = `try{if(localStorage.getItem("theme")==="light")document.documentElement.classList.remove("dark")}catch(e){}`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`dark ${inter.variable} ${jetbrainsMono.variable} h-full antialiased`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="flex min-h-full flex-col">
        <TooltipProvider delay={150}>
          <SiteHeader />
          <main className="mx-auto w-full max-w-7xl flex-1 px-4 pt-10 sm:px-6">{children}</main>
          <SiteFooter />
        </TooltipProvider>
      </body>
    </html>
  );
}
