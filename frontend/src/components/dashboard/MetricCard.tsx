interface MetricCardProps {
  label: string
  value: string | number
  change?: string
  changePositive?: boolean
}

export default function MetricCard({
  label,
  value,
  change,
  changePositive,
}: MetricCardProps) {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.03] p-6">
      <p className="text-sm font-medium text-white/50">{label}</p>
      <p className="mt-2 text-2xl font-semibold tabular-nums text-white">
        {value}
      </p>
      {change !== undefined && (
        <p
          className={`mt-1 text-sm tabular-nums ${
            changePositive === true
              ? 'text-emerald-400/90'
              : changePositive === false
                ? 'text-red-400/90'
                : 'text-white/50'
          }`}
        >
          {change}
        </p>
      )}
    </div>
  )
}
