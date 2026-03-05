// en-CA locale produces YYYY-MM-DD format — safe for string equality comparison
export function getOsloDateString(date: Date): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Europe/Oslo',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(date);
}

export interface UsageAggregate {
  tokens: number;
  costUsd: number;
  badLines: number;
}

export function aggregateTodayUsage(lines: string[]): UsageAggregate {
  const today = getOsloDateString(new Date());
  let tokens = 0;
  let costUsd = 0;
  let badLines = 0;

  for (const raw of lines) {
    const line = raw.trim();
    if (!line) continue;
    try {
      const entry = JSON.parse(line);
      if (entry.type !== 'model.usage') continue;
      if (!entry.ts) continue;
      if (getOsloDateString(new Date(entry.ts)) !== today) continue;
      // Accept totalTokens; fall back to inputTokens + outputTokens
      const t =
        entry.usage?.totalTokens ??
        (entry.usage?.inputTokens ?? 0) + (entry.usage?.outputTokens ?? 0);
      tokens += t;
      costUsd += entry.costUsd ?? 0;
    } catch {
      badLines++;
    }
  }

  return { tokens, costUsd, badLines };
}
