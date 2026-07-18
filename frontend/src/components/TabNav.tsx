import clsx from "clsx";
import { NavLink } from "react-router-dom";

export interface TabItem {
  to: string;
  label: string;
  end?: boolean;
}

export function TabNav({ tabs }: { tabs: TabItem[] }) {
  return (
    <div className="flex gap-1 overflow-x-auto border-b border-border px-2">
      {tabs.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          end={tab.end}
          className={({ isActive }) =>
            clsx(
              "shrink-0 whitespace-nowrap border-b-2 px-2.5 py-2 text-[12.5px] font-medium transition-colors",
              isActive
                ? "border-accent text-text"
                : "border-transparent text-text-tertiary hover:text-text-secondary",
            )
          }
        >
          {tab.label}
        </NavLink>
      ))}
    </div>
  );
}
