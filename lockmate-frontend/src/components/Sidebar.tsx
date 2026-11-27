// LOCKMATE Sidebar Navigation

import { NavLink, useLocation } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Upload, 
  FileCheck, 
  ShieldCheck,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import { useState } from 'react';

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/upload', label: 'Upload & Sanitize', icon: Upload },
  { path: '/results', label: 'Results', icon: FileCheck },
  { path: '/evaluation', label: 'Privacy & Evaluation', icon: ShieldCheck },
] as const;

interface SidebarProps {
  onToggle?: () => void;
  collapsed?: boolean;
}

export function Sidebar({ onToggle, collapsed = false }: SidebarProps) {
  const location = useLocation();
  const [internalCollapsed, setInternalCollapsed] = useState(false);

  const isCollapsed = collapsed || internalCollapsed;
  const handleToggle = () => {
    if (onToggle) {
      onToggle();
    } else {
      setInternalCollapsed(!internalCollapsed);
    }
  };

  return (
    <aside 
      className={`flex flex-col bg-secondary border-r border-primary transition-all duration-300 ${isCollapsed ? 'w-16' : 'w-64'}`}
      role="navigation"
      aria-label="Main navigation"
    >
      {/* Logo */}
      <div className="flex items-center justify-between h-16 px-4 border-b border-primary">
        {!isCollapsed && (
          <NavLink to="/" className="flex items-center gap-3 text-xl font-bold text-accent-primary" aria-label="LOCKMATE Home">
            <div className="w-8 h-8 rounded-lg bg-accent-muted flex items-center justify-center">
              <ShieldCheck className="w-5 h-5 text-accent-primary" />
            </div>
            <span>LOCKMATE</span>
          </NavLink>
        )}
        <button
          onClick={handleToggle}
          className="p-2 rounded-md hover:bg-tertiary text-secondary transition-colors"
          aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          aria-expanded={!isCollapsed}
        >
          {isCollapsed ? <ChevronRight className="w-5 h-5" /> : <ChevronLeft className="w-5 h-5" />}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map(({ path, label, icon: Icon }) => {
          const isActive = location.pathname === path || (path !== '/' && location.pathname.startsWith(path));
          return (
            <NavLink
              key={path}
              to={path}
              className={({ isActive }) => `
                flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200
                ${isActive 
                  ? 'bg-accent-muted text-accent-primary border border-accent-primary/30' 
                  : 'text-secondary hover:text-primary hover:bg-tertiary'
                }
                ${collapsed ? 'justify-center' : ''}
              `}
              title={collapsed ? label : undefined}
              aria-current={isActive ? 'page' : undefined}
            >
              <Icon className="w-5 h-5 flex-shrink-0" aria-hidden="true" />
              {!collapsed && <span>{label}</span>}
            </NavLink>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-3 border-t border-primary">
        {!collapsed && (
          <div className="text-xs text-muted text-center">
            LOCKMATE v1.0.0 — Secret Wards Track 3
          </div>
        )}
      </div>
    </aside>
  );
}