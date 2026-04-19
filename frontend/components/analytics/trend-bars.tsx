type TrendBarsProps = {
  label: string;
  values: number[];
  accentClassName?: string;
};

export function TrendBars({ label, values, accentClassName = 'bg-coral' }: TrendBarsProps) {
  const maxValue = Math.max(...values, 1);

  return (
    <section className="rounded-[18px] border-4 border-black bg-white p-4 shadow-brutal">
      <div className="inline-flex -rotate-1 rounded-[12px] border-2 border-black bg-sun px-3 py-1 text-[11px] font-black uppercase tracking-[0.22em] shadow-brutal">
        {label}
      </div>
      <div className="mt-4 flex items-end gap-2">
        {values.map((value, index) => (
          <div key={`${label}-${index}`} className="flex flex-1 flex-col items-center gap-2">
            <div
              className={`w-full rounded-t-[10px] border-2 border-black shadow-brutal ${accentClassName}`}
              style={{ height: `${Math.max((value / maxValue) * 160, 18)}px` }}
            />
            <span className="text-[11px] font-black uppercase tracking-[0.14em]">{index + 1}</span>
          </div>
        ))}
      </div>
    </section>
  );
}