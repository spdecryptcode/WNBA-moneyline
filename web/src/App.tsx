import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Shell } from "./components/Shell";
import { Backtest } from "./pages/Backtest";
import { DataQuality } from "./pages/DataQuality";
import { GameDetail } from "./pages/GameDetail";
import { Home } from "./pages/Home";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Shell />}>
          <Route path="/" element={<Home />} />
          <Route path="/game/:gameId" element={<GameDetail />} />
          <Route path="/backtest" element={<Backtest />} />
          <Route path="/data-quality" element={<DataQuality />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
