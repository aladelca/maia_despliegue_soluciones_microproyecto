export type DashboardView =
  | "summary"
  | "analysis"
  | "prediction"
  | "history"
  | "experiments"
  | "project";

type NavigationItem = {
  id: DashboardView;
  label: string;
  icon: string;
};

const navigationItems: NavigationItem[] = [
  { id: "summary", label: "Resumen", icon: "⌂" },
  { id: "analysis", label: "Análisis de datos", icon: "▥" },
  { id: "prediction", label: "Predicción", icon: "◎" },
  { id: "history", label: "Historial", icon: "↺" },
  { id: "experiments", label: "Experimentación", icon: "◇" },
  { id: "project", label: "Proyecto", icon: "ⓘ" },
];

type DashboardNavigationProps = {
  activeView: DashboardView;
  onNavigate: (view: DashboardView) => void;
};

export function DashboardNavigation({ activeView, onNavigate }: DashboardNavigationProps) {
  return (
    <aside className="dashboard-sidebar">
      <div className="brand-lockup">
        <span className="brand-mark" aria-hidden="true">↗</span>
        <span>
          <strong>IntentIQ</strong>
          <small>Purchase dashboard</small>
        </span>
      </div>

      <nav aria-label="Secciones del dashboard">
        {navigationItems.map((item) => (
          <button
            aria-current={activeView === item.id ? "page" : undefined}
            className="nav-item"
            key={item.id}
            onClick={() => onNavigate(item.id)}
            type="button"
          >
            <span className="nav-icon" aria-hidden="true">{item.icon}</span>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-note">
        <span className="status-dot" />
        <strong>Modelo en producción</strong>
        <p>Champion registrado en MLflow y servido desde AWS.</p>
      </div>
    </aside>
  );
}
