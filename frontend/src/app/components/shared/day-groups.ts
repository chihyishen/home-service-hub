const WEEKDAYS = '日一二三四五六';

export interface DayGroup<T> {
  key: string;
  label: string;
  items: T[];
}

/** Groups consecutive items sharing a local calendar day; keeps input order. */
export function groupByDay<T>(items: T[], dateOf: (item: T) => string | number | Date): DayGroup<T>[] {
  const groups: DayGroup<T>[] = [];
  for (const item of items) {
    const raw = dateOf(item);
    // 'YYYY-MM-DD' alone parses as UTC; read it as a local date instead.
    const d = typeof raw === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(raw)
      ? new Date(+raw.slice(0, 4), +raw.slice(5, 7) - 1, +raw.slice(8, 10))
      : new Date(raw);
    const key = `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
    const last = groups.at(-1);
    if (last?.key === key) {
      last.items.push(item);
    } else {
      groups.push({ key, label: `${d.getMonth() + 1}月${d.getDate()}日 週${WEEKDAYS[d.getDay()]}`, items: [item] });
    }
  }
  return groups;
}
