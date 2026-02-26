export default function MetricsSkeleton() {
  return (
    <div className="animate-pulse space-y-4">
      {/* Stat cards skeleton */}
      <div className="flex gap-3">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="flex-1 h-16 bg-gray-200 dark:bg-gray-700 rounded-lg" />
        ))}
      </div>
      {/* Bar chart skeleton */}
      <div className="h-48 bg-gray-200 dark:bg-gray-700 rounded-lg" />
      {/* Gauge skeleton */}
      <div className="h-40 w-40 rounded-full bg-gray-200 dark:bg-gray-700 mx-auto" />
    </div>
  );
}
