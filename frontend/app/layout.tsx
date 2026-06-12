import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";
import { AuthProvider } from "@/lib/auth";

export const metadata: Metadata = {
  title: "Pulse — Design Intelligence Platform",
  description: "KPMG Design Excellence & Quality",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <AuthProvider>
          <Nav />
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
