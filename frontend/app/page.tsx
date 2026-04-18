import Hero from '@/components/landing/Hero'
import FeatureTiles from '@/components/landing/FeatureTiles'
import ChatMockup from '@/components/landing/ChatMockup'
import BackgroundShapes from '@/components/landing/BackgroundShapes'

export default function HomePage() {
  return (
    <main className="min-h-screen relative overflow-hidden bg-[linear-gradient(180deg,#ffffff_0%,#fff6e9_100%)]">
      <BackgroundShapes />
      <Hero />
      <FeatureTiles />
      <ChatMockup />

      <footer className="container mx-auto px-6 lg:px-20 py-12 text-center text-sm text-gray-600">
        Built for demos — <a href="/demo" className="underline">try the demo workspace</a> or <a href="/auth/login" className="underline">sign in to your account</a>.
      </footer>
    </main>
  )
}
