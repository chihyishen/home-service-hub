import { describe, expect, it } from 'vitest';
import { groupByDay } from './day-groups';

describe('groupByDay', () => {
  it('groups consecutive same-day items and labels them with the weekday', () => {
    const rows = [{ d: '2026-11-19' }, { d: '2026-11-19' }, { d: '2026-11-18' }];
    const groups = groupByDay(rows, r => r.d);
    expect(groups.map(g => g.items.length)).toEqual([2, 1]);
    expect(groups[0].label).toBe('11月19日 週四');
  });
});
