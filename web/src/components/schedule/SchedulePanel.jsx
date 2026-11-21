import { useMemo } from 'react';

// Schedule panel: ordered timeline of assignments, rest breaks, and reason text.
// All scores and reason text come from the engine response — exposure_score is an estimate.
export default function SchedulePanel({ schedule, sites }) {
  const assignments = useMemo(() => {
    if (!schedule?.assignments) return [];
    const siteMap = Object.fromEntries(sites.map((s) => [s.site_id, s]));
    return [...schedule.assignments].sort((a, b) => a.start.localeCompare(b.start)).map((a) => ({
      ...a,
      site: siteMap[a.site_id],
    }));
  }, [schedule, sites]);

  if (!schedule || assignments.length === 0) {
    return (
      <div className="border rounded-lg p-4">
        <h2 className="font-semibold mb-2">Schedule</h2>
        <div className="h-32 rounded bg-slate-100 flex items-center justify-center text-slate-400 text-sm">
          Generate a schedule to see the timeline
        </div>
      </div>
    );
  }

  return (
    <div className="border rounded-lg p-4 space-y-3">
      <h2 className="font-semibold mb-2">Schedule</h2>
      <div className="space-y-2">
        {assignments.map((a, i) => {
          const siteName = a.site?.name ?? a.site_id;
          const jobType = a.site?.job_type ?? '';
          return (
            <div key={a.site_id} className="border rounded p-2 bg-slate-50">
              <div className="flex justify-between items-start mb-1">
                <div>
                  <div className="font-medium text-slate-900">{siteName}</div>
                  <div className="text-xs text-slate-500">{jobType}</div>
                </div>
                <div className="text-right text-xs font-mono text-slate-600">
                  {a.start} &ndash; {a.end}
                </div>
              </div>
              {a.rest_breaks && a.rest_breaks.length > 0 ? (
                <div className="text-xs text-blue-600 mb-1">
                  Rest breaks:{' '}
                  {a.rest_breaks.map((b, j) => (
                    <span key={j}>
                      {b.start}&ndash;{b.end}{j < a.rest_breaks.length - 1 ? ', ' : ''}
                    </span>
                  ))}
                </div>
              ) : null}
              <div className="text-xs text-slate-700 mb-1">{a.reason}</div>
              <div className="flex gap-3 text-xs">
                <span className="text-slate-600">Exposure: {a.exposure_score} <span className="text-xs text-orange-500">(estimate)</span></span>
                <span className="text-slate-600">Confidence: {(a.confidence * 100).toFixed(0)}%</span>
              </div>
              {i < assignments.length - 1 && <div className="h-px bg-slate-200 my-1" />}
            </div>
          );
        })}
      </div>
    </div>
  );
}