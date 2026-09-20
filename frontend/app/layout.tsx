import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Fraud Command Center',
  description: 'Explainable transaction monitoring and risk-based alert prioritization',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
