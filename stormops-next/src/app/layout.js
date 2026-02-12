import './globals.css'

export const metadata = {
  title: 'StormOps - Earth-2 Storm Intelligence',
  description: 'NVIDIA Earth-2 powered storm intelligence platform for roofing contractors',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="bg-dark-300 text-white">{children}</body>
    </html>
  )
}
