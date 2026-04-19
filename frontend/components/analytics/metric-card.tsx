type MetricCardProps = {
  label: string;
  value: string;
  hint?: string;
};

export function MetricCard({ label, value, hint }: MetricCardProps) {
  return (
    <article className="rounded-[18px] border-4 border-black bg-white p-4 shadow-brutal">
      <div className="inline-flex -rotate-1 rounded-[12px] border-2 border-black bg-sun px-3 py-1 text-[11px] font-black uppercase tracking-[0.22em] shadow-brutal">
        {label}
      </div>
      <p className="mt-3 text-4xl font-black tracking-[-0.04em]">{value}</p>
      {hint ? <p className="mt-2 text-sm leading-6">{hint}</p> : null}
      <div className="mt-4 h-3 rounded-full border-2 border-black bg-paper shadow-brutal">
        <div className="h-full w-2/3 rounded-full bg-coral" />
      </div>
    </article>
  );
}
