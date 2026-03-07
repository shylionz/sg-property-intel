import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Singapore Property Intelligence",
  description: "URA transaction analytics and rental yields",
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
