export default function ChatMockup() {
  return (
    <section className="container mx-auto px-6 lg:px-20 py-10">
      <div className="border-2 border-black rounded-md overflow-hidden shadow-neobrutal bg-white">
        <div className="grid grid-cols-12 gap-0">
          <aside className="col-span-3 p-4 border-r border-black bg-[#fafafa]">
            <div className="h-8 bg-white border border-black rounded-sm mb-3" />
            <div className="space-y-2">
              <div className="h-10 bg-white border border-black rounded-sm" />
              <div className="h-10 bg-white border border-black rounded-sm" />
              <div className="h-10 bg-white border border-black rounded-sm" />
            </div>
          </aside>

          <main className="col-span-6 p-6">
            <div className="h-64 overflow-auto space-y-4">
              <div className="text-sm text-gray-700">You: Summarize Q1 stakeholder feedback.</div>
              <div className="bg-black text-white p-3 rounded-md text-sm">Assistant: Top themes: clarity on roadmap, feature requests X, Y. Sources: (Feedback doc)</div>
              <div className="text-sm text-gray-700">You: Any action items?</div>
              <div className="bg-black text-white p-3 rounded-md text-sm">Assistant: Yes — prioritize A, assign to product. See citations below.</div>
            </div>
            <div className="mt-4">
              <div className="flex gap-2">
                <input className="flex-1 border border-black p-2 rounded-sm" placeholder="Ask about your documents..." />
                <button className="bg-black text-white px-4 rounded-sm">Send</button>
              </div>
            </div>
          </main>

          <aside className="col-span-3 p-4 border-l border-black bg-[#fff9f0]">
            <h4 className="font-semibold">Retrieval</h4>
            <div className="mt-3 space-y-2">
              <div className="h-8 bg-white border border-black rounded-sm" />
              <div className="h-8 bg-white border border-black rounded-sm" />
            </div>
          </aside>
        </div>
      </div>
    </section>
  )
}
