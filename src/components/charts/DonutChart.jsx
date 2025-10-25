export default function DonutChart({ data = [], size = 160, thickness = 20, showLegend = true, className = '' }) {
  if (!data || data.length === 0) {
    return (
      <div className={`flex items-center justify-center text-text-tertiary text-sm ${className}`} style={{ height: size }}>
        Sem dados
      </div>
    );
  }

  const total = data.reduce((sum, item) => sum + (item.value || 0), 0);

  if (total === 0) {
    return (
      <div className={`flex items-center justify-center text-text-tertiary text-sm ${className}`} style={{ height: size }}>
        Sem dados
      </div>
    );
  }

  const colors = [
    '#00D3A9', // accent
    '#00D084', // success
    '#F5A623', // warning
    '#0070F3', // info
    '#FF3B30', // error
    '#A8A8B3', // text-secondary
  ];

  let currentAngle = -90; // Começa no topo

  return (
    <div className={`flex ${showLegend ? 'flex-row gap-6' : 'flex-col'} items-center ${className}`}>
      {/* Gráfico SVG */}
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="transform -rotate-90">
        {/* Círculo de fundo */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={(size - thickness) / 2}
          fill="none"
          stroke="var(--color-background-subtle)"
          strokeWidth={thickness}
        />

        {/* Segmentos */}
        {data.map((item, index) => {
          const percentage = (item.value / total) * 100;
          const angle = (percentage / 100) * 360;
          const radius = (size - thickness) / 2;
          const circumference = 2 * Math.PI * radius;
          const strokeDasharray = `${(angle / 360) * circumference} ${circumference}`;
          const rotation = currentAngle;

          currentAngle += angle;

          return (
            <circle
              key={index}
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke={colors[index % colors.length]}
              strokeWidth={thickness}
              strokeDasharray={strokeDasharray}
              strokeDashoffset={0}
              style={{
                transform: `rotate(${rotation}deg)`,
                transformOrigin: '50% 50%',
                transition: 'all 0.5s ease-out'
              }}
            />
          );
        })}

        {/* Valor central */}
        <text
          x={size / 2}
          y={size / 2}
          textAnchor="middle"
          dominantBaseline="middle"
          className="fill-text-primary font-bold"
          style={{ fontSize: size / 6, transform: 'rotate(90deg)', transformOrigin: '50% 50%' }}
        >
          {total}
        </text>
      </svg>

      {/* Legenda */}
      {showLegend && (
        <div className="flex flex-col gap-2">
          {data.map((item, index) => {
            const percentage = ((item.value / total) * 100).toFixed(1);
            return (
              <div key={index} className="flex items-center gap-2 text-sm">
                <div
                  className="w-3 h-3 rounded-full flex-shrink-0"
                  style={{ backgroundColor: colors[index % colors.length] }}
                />
                <span className="text-text-secondary truncate">{item.label}</span>
                <span className="text-text-primary font-medium ml-auto">{percentage}%</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
