export default function SimpleBarChart({ data = [], maxHeight = 120, className = '' }) {
  if (!data || data.length === 0) {
    return (
      <div className={`flex items-center justify-center h-32 text-text-tertiary text-sm ${className}`}>
        Sem dados para exibir
      </div>
    );
  }

  const maxValue = Math.max(...data.map(d => d.value || 0), 1);

  return (
    <div className={`flex items-end justify-between gap-2 ${className}`} style={{ height: maxHeight }}>
      {data.map((item, index) => {
        const heightPercent = (item.value / maxValue) * 100;

        return (
          <div key={index} className="flex-1 flex flex-col items-center gap-2 group">
            {/* Tooltip com valor */}
            <div className="opacity-0 group-hover:opacity-100 transition-opacity text-xs bg-background-elevated border border-border rounded px-2 py-1 mb-1">
              {item.value}
            </div>

            {/* Barra */}
            <div
              className="w-full bg-accent rounded-t transition-all duration-500 ease-out hover:bg-accent-hover"
              style={{ height: `${heightPercent}%`, minHeight: item.value > 0 ? '4px' : '0px' }}
            />

            {/* Label */}
            <div className="text-xs text-text-tertiary truncate w-full text-center">
              {item.label}
            </div>
          </div>
        );
      })}
    </div>
  );
}
