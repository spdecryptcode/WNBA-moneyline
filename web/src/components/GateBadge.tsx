export function GateBadge({ bet }: { bet: boolean }) {
  return (
    <span className={`gate ${bet ? "gate-bet" : "gate-pass"}`}>
      {bet ? "BET" : "PASS"}
    </span>
  );
}
