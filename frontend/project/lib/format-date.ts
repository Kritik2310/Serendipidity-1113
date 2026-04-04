export function formatDate(date: string | number | Date) {
  const d = new Date(date);

  return d.toISOString().replace("T", " ").slice(0, 19);
}