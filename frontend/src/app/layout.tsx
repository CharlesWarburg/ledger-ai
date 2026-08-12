import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Ledger AI",
  description: "A focused financial workspace for small teams.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
