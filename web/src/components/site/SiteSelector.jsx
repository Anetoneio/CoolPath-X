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
      setScheduleError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <h2 className="font-semibold">Select Sites</h2>
      <div className="max-h-48 overflow-y-auto border rounded p-2 space-y-1">
        {sites.map((site) => (
          <label key={site.site_id} className="flex items-center gap-2 cursor-pointer select-none hover:bg-slate-50 p-1 rounded">
            <input
              type="checkbox"
              checked={selectedIds.includes(site.site_id)}
              onChange={() => toggleSite(site.site_id)}
              className="rounded text-slate-900"
            />
            <div className="text-sm">
              <div className="font-medium">{site.name}</div>
              <div className="text-xs text-slate-500">
                {site.job_type} &middot; priority {site.priority} &middot;
                {site.duration_min} min
              </div>
            </div>
          </label>
        ))}
      </div>

      <h2 className="font-semibold">Shift</h2>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-slate-500 mb-1">Date</label>
          <input
            type="date"
            value={shift.date}
            onChange={(e) => setShift({ ...shift, date: e.target.value })}
            className="w-full border rounded px-2 py-1 text-sm"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-500">Start</label>
          <input
            type="time"
            value={shift.shift_start}
            onChange={(e) => setShift({ ...shift, shift_start: e.target.value })}
            className="w-full border rounded px-2 py-1 text-sm"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-500">End</label>
          <input
            type="time"
            value={shift.shift_end}
            onChange={(e) => setShift({ ...shift, shift_end: e.target.value })}
            className="w-full border rounded px-2 py-1 text-sm"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-500">Crews</label>
          <input
            type="number"
            value={shift.crews}
            onChange={(e) => setShift({ ...shift, crews: e.target.value })}
            className="w-full border rounded px-2 py-1 text-sm"
          />
        </div>
      </div>

      <button
        onClick={handleGenerate}
        disabled={loading || selectedIds.length === 0}
        className="w-full bg-slate-900 text-white px-4 py-2 rounded disabled:bg-slate-400 hover:!bg-slate-800 text-sm font-medium"
      >
        {loading ? 'Generating…' : `Generate Schedule (${selectedIds.length} site${selectedIds.length !== 1 ? 's' : ''})`}
      </button>

      {scheduleError && (
        <div className="p-2 rounded bg-red-50 border border-red-200 text-red-800 text-sm">
          {scheduleError}
        </div>
      )}

      {scheduleResult && (
        <div className="p-3 rounded bg-green-50 border border-green-200">
          <div className="text-xs font-semibold text-green-800 mb-1">Schedule generated</div>
          <div className="text-xs text-slate-700">
            {scheduleResult.assignments?.length ?? 0} assignment(s)
          </div>
        </div>
      )}
    </div>
  );
}