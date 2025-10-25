export default function StatCard({ icon: Icon, label, value, trend }) {
  return (
    <div className="bg-background-elevated border border-border rounded-lg p-6 hover:border-accent hover:-translate-y-0.5 transition-all duration-200">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm text-text-secondary mb-1">{label}</p>
          <p className="text-2xl font-bold text-text-primary">{value}</p>
          {trend && (
            <p className={`text-sm mt-1 ${trend.direction === 'up' ? 'text-green-500' : 'text-red-500'}`}>
              {trend.value}
            </p>
          )}
        </div>
        {Icon && (
          <div className="p-2 bg-accent-subtle rounded-lg">
            <Icon className="w-5 h-5 text-accent" />
          </div>
        )}
      </div>
    </div>
  );
}
