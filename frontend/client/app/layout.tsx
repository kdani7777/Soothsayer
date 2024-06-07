import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { playfair_display } from './ui/fonts'

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Soothsayer",
  description: "Your personal race consultant",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={playfair_display.className}>{children}</body>
    </html>
  );
}
