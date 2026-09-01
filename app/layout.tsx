import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';
import './control.css';
import './workspace.css';
import './polish.css';
import './landing.css';

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  title: 'C2CDirect — Opportunity intelligence for independent engineers',
  description: 'Find high-rate C2C engineering opportunities, verify the vendor chain, and manage every pursuit from one evidence-backed workspace.',
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? 'https://directc2c.com'),
  icons: { icon: '/favicon.svg' },
  openGraph: {
    title: 'C2CDirect',
    description: 'Find the contract. Verify the chain. Win the work.',
    images: ['/og.png'],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'C2CDirect',
    description: 'Find the contract. Verify the chain. Win the work.',
    images: ['/og.png'],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
