import { NavLink, Outlet } from "react-router-dom";
import clsx from "clsx";
import { Activity, Building2, Moon, Sun, Users, Wrench } from "lucide-react";
import { useTheme } from "./lib/theme";

const NAV = [
  { to: "/patients", label: "Patients", icon: Users },
  { to: "/placer-ops", label: "Placer Ops", icon: Activity },
  { to: "/facilities", label: "Facilities", icon: Building2 },
  { to: "/admin", label: "Admin", icon: Wrench },
];

export default function App() {
  const { theme, toggle } = useTheme();

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-bg text-text">
      <aside className="flex w-[212px] shrink-0 flex-col border-r border-border bg-bg">
        <div className="flex items-center gap-2 px-4 py-4">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-accent text-[11px] font-bold text-white">
            I
          </div>
          <span className="text-[13px] font-semibold tracking-tight">Iliad</span>
        </div>

        <nav className="flex flex-1 flex-col gap-0.5 px-2">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-2 rounded-md px-2.5 py-1.5 text-[12.5px] font-medium transition-colors",
                  isActive
                    ? "bg-accent-soft text-accent"
                    : "text-text-secondary hover:bg-bg-hover hover:text-text",
                )
              }
            >
              <Icon size={15} strokeWidth={2} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-border p-2">
          <button
            onClick={toggle}
            className="flex w-full cursor-pointer items-center gap-2 rounded-md px-2.5 py-1.5 text-[12.5px] font-medium text-text-secondary transition-colors hover:bg-bg-hover hover:text-text"
          >
            {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
            {theme === "dark" ? "Light mode" : "Dark mode"}
          </button>
        </div>
      </aside>

      <main className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <Outlet />
      </main>
    </div>
  );
}
