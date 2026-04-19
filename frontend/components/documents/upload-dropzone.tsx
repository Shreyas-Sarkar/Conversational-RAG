export function UploadDropzone() {
  return (
    <section className="rounded-[18px] border-4 border-black bg-white p-4 shadow-brutal">
      <div className="inline-flex -rotate-2 rounded-[12px] border-2 border-black bg-coral px-3 py-1 text-[11px] font-black uppercase tracking-[0.22em] shadow-brutal">
        Document upload
      </div>
      <div className="mt-3 rounded-[18px] border-4 border-dashed border-black bg-paper p-6 text-center shadow-brutal">
        <p className="text-2xl font-black uppercase tracking-[-0.02em]">DROP DOCS HERE</p>
        <p className="mt-2 text-sm font-medium">PDF, TXT, and DOCX supported.</p>
      </div>
      <div className="mt-4 grid gap-2 text-sm font-black uppercase tracking-[0.08em]">
        <p className="rounded-[12px] border-2 border-black bg-sun px-3 py-2 shadow-brutal">Uploading</p>
        <p className="rounded-[12px] border-2 border-black bg-white px-3 py-2 shadow-brutal">Chunking</p>
        <p className="rounded-[12px] border-2 border-black bg-white px-3 py-2 shadow-brutal">Embedding</p>
        <p className="rounded-[12px] border-2 border-black bg-white px-3 py-2 shadow-brutal">Indexing</p>
        <p className="rounded-[12px] border-2 border-black bg-moss px-3 py-2 shadow-brutal">Done</p>
      </div>
    </section>
  );
}