import { NavLink, Outlet } from "react-router-dom";
import clsx from "clsx";
import { Moon, Sun, Users, Wrench } from "lucide-react";
import { useTheme } from "./lib/theme";

const NAV = [
  { to: "/patients", label: "Patients", icon: Users },
  { to: "/admin", label: "Admin", icon: Wrench },
];

export default function App() {
  const { theme, toggle } = useTheme();

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-bg text-text">
      <header className="flex h-11 shrink-0 items-center gap-5 border-b border-border bg-bg px-4">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-accent text-[11px] font-bold text-white">
            I
          </div>
          <span className="text-[13px] font-semibold tracking-tight">Iliad</span>
        </div>

        <nav className="flex items-center gap-1">
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

        <button
          onClick={toggle}
          aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          title={theme === "dark" ? "Light mode" : "Dark mode"}
          className="ml-auto flex cursor-pointer items-center gap-2 rounded-md px-2.5 py-1.5 text-[12.5px] font-medium text-text-secondary transition-colors hover:bg-bg-hover hover:text-text"
        >
          {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
        </button>
      </header>

      <main className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <Outlet />
      </main>
    </div>
  );
}
