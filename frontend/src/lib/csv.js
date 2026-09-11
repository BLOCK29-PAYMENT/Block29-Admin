// Safe CSV generation and download.
// - RFC 4180 quoting: embedded double quotes are doubled
// - Formula-injection guard: cells starting with = + - @ are prefixed with '
//   so Excel/Sheets treat them as text, not executable formulas

function escapeCell(value) {
  let s = String(value ?? '');
  if (/^[=+\-@]/.test(s)) {
    s = `'${s}`;
  }
  return `"${s.replace(/"/g, '""')}"`;
}

export function toCsv(rows) {
  if (!rows || rows.length === 0) return '';
  const headers = Object.keys(rows[0]);
  return [
    headers.map(escapeCell).join(','),
    ...rows.map((row) => headers.map((h) => escapeCell(row[h])).join(',')),
  ].join('\n');
}

export function downloadCsv(rows, filename) {
  const csv = toCsv(rows);
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  window.URL.revokeObjectURL(url);
}
