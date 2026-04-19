export function ChatComposer() {
  return (
    <form className="sticky bottom-0 mt-4 rounded-[18px] border-4 border-black bg-white p-3 shadow-brutal">
      <label className="mb-2 inline-flex -rotate-1 rounded-[12px] border-2 border-black bg-sky px-3 py-1 text-[11px] font-black uppercase tracking-[0.22em] shadow-brutal">
        Ask something
      </label>
      <div className="flex gap-3">
        <input
          className="min-w-0 flex-1 rounded-[14px] border-4 border-black bg-paper px-4 py-3 font-medium outline-none"
          placeholder="Explain Oracle migration..."
        />
        <button className="rounded-[14px] border-4 border-black bg-coral px-5 py-3 font-black uppercase tracking-[0.08em] shadow-brutal transition-transform hover:-translate-x-1 hover:-translate-y-1">
          Send
        </button>
      </div>
    </form>
  );
}
