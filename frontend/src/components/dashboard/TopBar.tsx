interface TopBarProps {
  title: string
  dateRange?: string
  onDateRangeChange?: (value: string) => void
  clientFilter?: string
  onClientFilterChange?: (value: string) => void
  ctaLabel?: string
  onCtaClick?: () => void
}

export default function TopBar({
  title,
  dateRange = 'Last 30 days',
  onDateRangeChange,
  clientFilter = 'All clients',
  onClientFilterChange,
  ctaLabel = 'Upgrade',
  onCtaClick,
}: TopBarProps) {
  return (
    <header className="flex h-14 flex-shrink-0 items-center justify-between border-b border-white/[0.06] bg-[#0b0f14] px-8">
      <h1 className="text-lg font-semibold text-white">{title}</h1>
      <div className="flex items-center gap-4">
        <select
          value={dateRange}
          onChange={(e) => onDateRangeChange?.(e.target.value)}
          className="rounded-lg border border-white/[0.08] bg-white/[0.04] px-3 py-2 text-sm text-white/80 focus:border-white/20 focus:outline-none focus:ring-1 focus:ring-white/20"
        >
          <option value="Last 7 days">Last 7 days</option>
          <option value="Last 30 days">Last 30 days</option>
          <option value="Last 90 days">Last 90 days</option>
        </select>
        <select
          value={clientFilter}
          onChange={(e) => onClientFilterChange?.(e.target.value)}
          className="rounded-lg border border-white/[0.08] bg-white/[0.04] px-3 py-2 text-sm text-white/80 focus:border-white/20 focus:outline-none focus:ring-1 focus:ring-white/20"
        >
          <option value="All clients">All clients</option>
          <option value="Production">Production</option>
          <option value="Staging">Staging</option>
        </select>
        <button
          type="button"
          onClick={onCtaClick}
          className="rounded-lg bg-white px-4 py-2 text-sm font-medium text-[#0b0f14] hover:bg-white/90 transition-colors"
        >
          {ctaLabel}
        </button>
      </div>
    </header>
  )
}
