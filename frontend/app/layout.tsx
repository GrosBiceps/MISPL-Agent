import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MISPL Agent",
  description: "Assistant IA pour le paramétrage GLIMS/MISPL",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
