import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Conversational-RAG',
  description: 'A portfolio-grade conversational document intelligence platform.'
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
