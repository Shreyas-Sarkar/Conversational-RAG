import Link from 'next/link'

export default function Hero() {
  return (
    <section className="relative overflow-hidden py-24">
      <div className="container mx-auto px-6 lg:px-20 flex items-center gap-12">
        <div className="max-w-2xl">
          <h1 className="text-5xl lg:text-6xl font-extrabold tracking-tight text-gray-900 mb-4">Conversational RAG for teams</h1>
          <p className="text-lg text-gray-700 mb-8">Search, chat and reason over your documents with transparent citations, streaming responses, and built-in analytics — designed for production demos and internal pilots.</p>
          <div className="flex items-center gap-4">
            <Link href="/demo" className="inline-block bg-black text-white px-6 py-3 rounded-sm font-semibold">Try demo</Link>
            <Link href="/auth/login" className="inline-block border-2 border-black px-6 py-3 rounded-sm font-semibold">Sign in</Link>
          </div>
        </div>

        <div className="hidden lg:block flex-1">
          <div className="shadow-neobrutal rounded-md bg-white p-2">
            <div className="bg-[#f7f7f7] border border-black rounded overflow-hidden">
              <div className="flex gap-2 items-center px-3 py-2 bg-black text-white">
                <div className="w-3 h-3 rounded-full bg-red-500" />
                <div className="w-3 h-3 rounded-full bg-yellow-400" />
                <div className="w-3 h-3 rounded-full bg-green-400" />
                <span className="ml-auto text-xs opacity-80">Demo • Recruiter</span>
              </div>

              <div className="p-4">
                <div className="h-48 bg-white rounded-md p-3 overflow-auto">
                  <div className="space-y-3">
                    <div className="text-sm text-gray-700">You: Show me the latest hiring pipeline.</div>
                    <div className="bg-black text-white p-3 rounded-md text-sm">Assistant: Here's a summary of candidates matching your criteria with links to resumes and citations.</div>
                    <div className="text-sm text-gray-700">You: Any standout matches?</div>
                    <div className="bg-black text-white p-3 rounded-md text-sm">Assistant: Yes — Candidate A has excellent product experience. Sources: (Doc 1)</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
