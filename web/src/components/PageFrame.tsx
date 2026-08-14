import type { ReactNode } from "react";

export function PageFrame({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <div className="content-wrap">
      <header className="page-head">
        <h1>{title}</h1>
        {subtitle ? <p>{subtitle}</p> : null}
      </header>
      {children}
    </div>
  );
}
