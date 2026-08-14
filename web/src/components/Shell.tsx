import { NavLink, Outlet } from "react-router-dom";

export function Shell() {
  return (
    <div className="app-shell">
      <header className="top-nav">
        <div className="nav-mark">
          WNBA <em>EDGE</em>
        </div>
        <nav className="nav-links">
          <NavLink to="/" end>
            Slate
          </NavLink>
          <NavLink to="/backtest">Backtest</NavLink>
          <NavLink to="/data-quality">Quality</NavLink>
        </nav>
      </header>
      <main className="main-pane">
        <Outlet />
      </main>
    </div>
  );
}
