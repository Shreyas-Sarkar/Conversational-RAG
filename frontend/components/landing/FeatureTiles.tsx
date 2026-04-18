export default function FeatureTiles() {
  const tiles = [
    {
      title: 'Transparent RAG',
      desc: 'Cite exact source documents and passages for every answer so your team can verify results.',
    },
    {
      title: 'Streaming Responses',
      desc: 'See answers arrive token-by-token for a responsive, demo-friendly experience.',
    },
    {
      title: 'Analytics & Metrics',
      desc: 'Track usage, retrieval quality, and query trends across demo workspaces.',
    },
  ]

  return (
    <section className="container mx-auto px-6 lg:px-20 py-12">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {tiles.map((t) => (
          <div key={t.title} className="border-2 border-black p-6 bg-white rounded-sm shadow-neobrutal">
            <h3 className="text-xl font-bold mb-2">{t.title}</h3>
            <p className="text-gray-700">{t.desc}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
