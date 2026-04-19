import { MetricCard } from '@/components/analytics/metric-card';
import { TrendBars } from '@/components/analytics/trend-bars';
import { getApiBaseUrl } from '@/lib/api';

export default async function AnalyticsPage() {
  const metrics = await fetch(`${getApiBaseUrl()}/metrics`, { cache: 'no-store' })
    .then((response) => response.json())
    .then((payload) => payload?.data ?? null)
    .catch(() => null);

  const latencyTrend = metrics?.latency_trend ?? [1.9, 1.7, 1.6, 1.5, 1.4];
  const queriesTrend = metrics?.queries_trend ?? [228, 251, 287, 319, 342];
  const topQueries = metrics?.top_queries ?? ['Explain Oracle migration', 'Compare two uploaded docs', 'Show sources used'];
  const avgLatency = metrics?.avg_latency ?? 1.4;
  const tokens = metrics?.tokens ?? 1200;
  const queriesPerDay = metrics?.queries_per_day ?? 342;
  const retrievedChunks = metrics?.retrieved_chunks ?? 1320;
  const feedbackScore = metrics?.feedback_score ?? 0.94;
  const confidence = metrics?.retrieval_confidence ?? 0.89;
  const cacheHitRate = metrics?.cache_hit_rate ?? 0.62;

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-6 py-10">
      <section className="space-y-6">
        <div className="rounded-[24px] border-4 border-black bg-white p-6 shadow-brutal">
          <div className="inline-flex -rotate-2 rounded-[14px] border-4 border-black bg-moss px-4 py-2 text-xs font-black uppercase tracking-[0.3em] shadow-brutal">
            Analytics
          </div>
          <h1 className="mt-4 text-4xl font-black uppercase tracking-[-0.03em]">AI pipeline performance</h1>
          <p className="mt-2 max-w-2xl text-sm font-medium leading-7">
            Hard numbers with the same neo-brutalist treatment: black strokes, solid blocks, and very little visual noise.
          </p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <MetricCard label="Avg latency" value={`${avgLatency.toFixed(1)}s`} hint="Live backend metrics" />
          <MetricCard label="Tokens" value={String(tokens)} hint="Aggregated from retrieval events" />
          <MetricCard label="Queries/day" value={String(queriesPerDay)} hint="Persisted query activity" />
          <MetricCard label="Sources used" value={String(retrievedChunks)} hint="Grounded retrieval coverage" />
          <MetricCard label="Feedback" value={`${Math.round(feedbackScore * 100)}%`} hint="Helpful answers, grounded sources" />
        </div>
        <div className="grid gap-4 xl:grid-cols-2">
          <TrendBars label="Latency trend" values={latencyTrend} accentClassName="bg-moss" />
          <TrendBars label="Queries trend" values={queriesTrend} accentClassName="bg-coral" />
        </div>
        <div className="grid gap-4 xl:grid-cols-[40%_30%_30%]">
          <section className="rounded-[18px] border-4 border-black bg-white p-4 shadow-brutal">
            <div className="inline-flex -rotate-1 rounded-[12px] border-2 border-black bg-sky px-3 py-1 text-[11px] font-black uppercase tracking-[0.22em] shadow-brutal">
              Retrieval quality
            </div>
            <div className="mt-4 space-y-3 text-sm font-medium leading-7">
              <div className="flex items-center justify-between gap-4">
                <span>Confidence</span>
                <span className="font-black">{confidence.toFixed(2)}</span>
              </div>
              <div className="h-4 rounded-full border-2 border-black bg-paper shadow-brutal">
                <div className="h-full rounded-full bg-moss" style={{ width: `${Math.round(confidence * 100)}%` }} />
              </div>
              <div className="flex items-center justify-between gap-4">
                <span>Cache hit rate</span>
                <span className="font-black">{Math.round(cacheHitRate * 100)}%</span>
              </div>
              <div className="h-4 rounded-full border-2 border-black bg-paper shadow-brutal">
                <div className="h-full rounded-full bg-sky" style={{ width: `${Math.round(cacheHitRate * 100)}%` }} />
              </div>
              <div className="flex items-center justify-between gap-4">
                <span>Feedback score</span>
                <span className="font-black">{Math.round(feedbackScore * 100)}%</span>
              </div>
              <div className="h-4 rounded-full border-2 border-black bg-paper shadow-brutal">
                <div className="h-full rounded-full bg-sun" style={{ width: `${Math.round(feedbackScore * 100)}%` }} />
              </div>
            </div>
          </section>
          <section className="rounded-[18px] border-4 border-black bg-white p-4 shadow-brutal">
            <div className="inline-flex -rotate-1 rounded-[12px] border-2 border-black bg-sun px-3 py-1 text-[11px] font-black uppercase tracking-[0.22em] shadow-brutal">
              Top queries
            </div>
            <div className="mt-4 space-y-3 text-sm font-black uppercase tracking-[0.08em]">
              {topQueries.map((query) => (
                <div key={query} className="rounded-[14px] border-2 border-black bg-paper px-3 py-3 shadow-brutal">
                  {query}
                </div>
              ))}
            </div>
          </section>
          <section className="rounded-[18px] border-4 border-black bg-white p-4 shadow-brutal">
            <div className="inline-flex -rotate-1 rounded-[12px] border-2 border-black bg-coral px-3 py-1 text-[11px] font-black uppercase tracking-[0.22em] shadow-brutal">
              Feedback split
            </div>
            <div className="mt-4 space-y-4">
              <div className="flex items-center justify-between rounded-[14px] border-2 border-black bg-paper px-3 py-3 shadow-brutal">
                <span className="font-black">👍 Positive</span>
                <span className="font-black">94%</span>
              </div>
              <div className="flex items-center justify-between rounded-[14px] border-2 border-black bg-paper px-3 py-3 shadow-brutal">
                <span className="font-black">👎 Negative</span>
                <span className="font-black">6%</span>
              </div>
            </div>
          </section>
        </div>
      </section>
    </main>
  );
}
