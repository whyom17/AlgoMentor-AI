import type { Metadata } from 'next';
import '@/styles/globals.css';

export const metadata: Metadata = {
  title: 'AlgoMentor AI — DSA Learning Platform',
  description:
    'Master data structures and algorithms with execution-aware AI mentorship, spaced repetition, and adaptive problem recommendations.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="min-h-screen bg-surface-900 text-gray-100 antialiased">
        {children}
      </body>
    </html>
  );
}
