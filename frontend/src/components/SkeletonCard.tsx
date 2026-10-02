const SkeletonCard = () => (
  <div className="p-3 rounded-lg border border-transparent animate-pulse">
    <div className="flex items-center gap-3">
      <div className="w-5 h-5 rounded bg-zinc-800 shrink-0" />
      <div className="min-w-0 flex-1">
        <div className="h-3.5 bg-zinc-800 rounded w-3/4 mb-2" />
        <div className="flex gap-2">
          <div className="h-2.5 bg-zinc-800/60 rounded w-14" />
          <div className="h-2.5 bg-zinc-800/60 rounded w-10" />
        </div>
      </div>
    </div>
  </div>
);

export default SkeletonCard;
