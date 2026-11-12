import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "FairValue Football",
    template: "%s · FairValue Football",
  },
  description:
    "Transfer-market intelligence: how market values and fees compare with measurable performance, with uncertainty shown.",
};

// Dark-first: the `dark` class is set on <html>. A light theme toggle arrives with
// the design system (Step 7); both themes share the same tokens in globals.css.
export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`dark ${inter.variable} ${jetbrainsMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col">{children}</body>
    </html>
  );
}
