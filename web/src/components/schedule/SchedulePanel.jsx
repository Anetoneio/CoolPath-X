import { useMemo } from 'react';

// Schedule panel: ordered timeline of assignments, rest breaks, and reason text.
// All scores and reason text come from the engine response — exposure_score is an estimate.
export default function SchedulePanel({ schedule, sites }) {
  const assignments = useMemo(() => {
    if (!schedule?.assignments) return [];
    const siteMap = Object.fromEntries(sites.map((s) => [s.site_id, s]));
    return [...schedule.assignments]
      .sort((a, b) => a.start.localeCompare(b.start))
      .map((a) => ({
        ...a,
        site: siteMap[a.site_id],
      }));
  }, [schedule, sites]);

  if (!schedule || assignments.length === 0) {
    return (
      <section className="rounded-xl border border-white/10 bg-white/5 p-3.5">
        <h2 className="text-sm font-semibold text-slate-100 mb-2">Schedule</h2>
        <div className="h-24 rounded-lg bg-slate-950/50 border border-white/5 flex items-center justify-center text-slate-400 text-xs text-center px-3">
          Generate a schedule to see the timeline
        </div>
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-white/10 bg-white/5 p-3.5 space-y-2.5">
      <h2 className="text-sm font-semibold text-slate-100">Schedule</h2>
      <div className="space-y-2">
        {assignments.map((a) => {
          const siteName = a.site?.name ?? a.site_id;
          const jobType = a.site?.job_type ?? '';
          return (
            <div
              key={a.site_id}
              className="rounded-lg border border-white/10 bg-slate-950/55 p-2.5 space-y-1.5"
            >
              <div className="flex justify-between items-start gap-2">
                <div>
                  <div className="text-xs sm:text-sm font-medium text-slate-100">
                    {siteName}
                  </div>
                  {jobType && (
                    <div className="text-xs text-slate-400">{jobType}</div>
                  )}
                </div>
                <div className="text-right text-xs font-mono text-sky-300 shrink-0">
                  {a.start} &ndash; {a.end}
                </div>
              </div>

              {a.rest_breaks && a.rest_breaks.length > 0 && (
                <div className="text-xs text-sky-300">
                  Rest breaks:{' '}
                  {a.rest_breaks.map((b, j) => (
                    <span key={j}>
                      {b.start}&ndash;{b.end}
                      {j < a.rest_breaks.length - 1 ? ', ' : ''}
                    </span>
                  ))}
                </div>
              )}

              <div className="text-xs text-slate-200 leading-relaxed">
                {a.reason}
              </div>

              <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs pt-0.5">
                <span className="text-slate-300">
                  Exposure: {a.exposure_score}{' '}
                  <span className="text-amber-300">(estimate)</span>
                </span>
                <span className="text-slate-300">
                  Confidence: {(a.confidence * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
