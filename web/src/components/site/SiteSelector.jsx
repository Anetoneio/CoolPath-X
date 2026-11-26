import { useState } from 'react';
import { postSchedule } from '../../config';

// Shift defaults match the mock schedule request in contracts/api.md.
// These are placeholders; the engine currently returns a static mock response.
const DEFAULT_SHIFT = {
  date: '2026-05-21',
  shift_start: '07:00',
  shift_end: '12:00',
  crews: 2,
};

export default function SiteSelector({ sites, onSchedule }) {
  const [selectedIds, setSelectedIds] = useState([]);
  const [shift, setShift] = useState({ ...DEFAULT_SHIFT });
  const [loading, setLoading] = useState(false);
  const [scheduleResult, setScheduleResult] = useState(null);
  const [scheduleError, setScheduleError] = useState(null);

  const toggleSite = (id) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const handleGenerate = async (e) => {
    e.preventDefault();
    setLoading(true);
    setScheduleError(null);
    setScheduleResult(null);
    try {
      const result = await postSchedule({
        date: shift.date,
        shift_start: shift.shift_start,
        shift_end: shift.shift_end,
        crews: Number(shift.crews),
        site_ids: selectedIds,
      });
      setScheduleResult(result);
      onSchedule?.(result);
    } catch (err) {
      console.error('Schedule request failed:', err);
      setScheduleError(err.message || 'Failed to generate schedule.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="rounded-xl border border-white/10 bg-white/5 p-3.5 space-y-3.5">
      <div className="space-y-2">
        <h2 className="text-sm font-semibold text-slate-100">Select Sites</h2>
        <div className="max-h-44 overflow-y-auto rounded-lg border border-white/10 bg-slate-950/50 p-1.5 space-y-1">
          {sites.length === 0 ? (
            <div className="px-2 py-3 text-xs text-slate-400 text-center">
              No sites loaded yet
            </div>
          ) : (
            sites.map((site) => (
              <label
                key={site.site_id}
                className="flex items-start gap-2.5 cursor-pointer select-none hover:bg-white/5 p-1.5 rounded-lg transition-colors"
              >
                <input
                  type="checkbox"
                  checked={selectedIds.includes(site.site_id)}
                  onChange={() => toggleSite(site.site_id)}
                  className="mt-0.5 h-4 w-4 rounded border-white/30 bg-slate-950 text-sky-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
                />
                <div className="text-xs leading-snug">
                  <div className="font-medium text-slate-100">{site.name}</div>
                  <div className="text-slate-400">
                    {site.job_type} &middot; priority {site.priority} &middot; {site.duration_min} min
                  </div>
                </div>
              </label>
            ))
          )}
        </div>
      </div>

      <div className="space-y-2">
        <h2 className="text-sm font-semibold text-slate-100">Shift</h2>
        <div className="grid grid-cols-2 gap-2.5">
          <div>
            <label htmlFor="shift-date" className="block text-xs text-slate-300 mb-1">
              Date
            </label>
            <input
              id="shift-date"
              type="date"
              value={shift.date}
              onChange={(e) => setShift({ ...shift, date: e.target.value })}
              className="w-full rounded-lg border border-white/15 bg-slate-950/60 px-2.5 py-1.5 text-xs text-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
            />
          </div>
          <div>
            <label htmlFor="shift-start" className="block text-xs text-slate-300 mb-1">
              Start
            </label>
            <input
              id="shift-start"
              type="time"
              value={shift.shift_start}
              onChange={(e) => setShift({ ...shift, shift_start: e.target.value })}
              className="w-full rounded-lg border border-white/15 bg-slate-950/60 px-2.5 py-1.5 text-xs text-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
            />
          </div>
          <div>
            <label htmlFor="shift-end" className="block text-xs text-slate-300 mb-1">
              End
            </label>
            <input
              id="shift-end"
              type="time"
              value={shift.shift_end}
              onChange={(e) => setShift({ ...shift, shift_end: e.target.value })}
              className="w-full rounded-lg border border-white/15 bg-slate-950/60 px-2.5 py-1.5 text-xs text-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
            />
          </div>
          <div>
            <label htmlFor="shift-crews" className="block text-xs text-slate-300 mb-1">
              Crews
            </label>
            <input
              id="shift-crews"
              type="number"
              min="1"
              value={shift.crews}
              onChange={(e) => setShift({ ...shift, crews: e.target.value })}
              className="w-full rounded-lg border border-white/15 bg-slate-950/60 px-2.5 py-1.5 text-xs text-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
            />
          </div>
        </div>
      </div>

      <button
        type="button"
        onClick={handleGenerate}
        disabled={loading || selectedIds.length === 0}
        className="w-full rounded-xl bg-sky-500 px-4 py-2 text-xs sm:text-sm font-semibold text-slate-950 hover:bg-sky-400 disabled:bg-slate-700 disabled:text-slate-400 disabled:cursor-not-allowed transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
      >
        {loading
          ? 'Generating…'
          : `Generate Schedule (${selectedIds.length} site${selectedIds.length !== 1 ? 's' : ''})`}
      </button>

      {scheduleError && (
        <div
          role="alert"
          className="p-2.5 rounded-lg bg-red-950/80 border border-red-400/40 text-red-100 text-xs"
        >
          {scheduleError}
        </div>
      )}

      {scheduleResult && (
        <div className="p-2.5 rounded-lg bg-emerald-950/60 border border-emerald-400/30">
          <div className="text-xs font-semibold text-emerald-300 mb-0.5">
            Schedule generated
          </div>
          <div className="text-xs text-slate-200">
            {scheduleResult.assignments?.length ?? 0} assignment(s)
          </div>
        </div>
      )}
    </section>
  );
}
