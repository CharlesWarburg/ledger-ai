import type { ReactNode } from "react";

export function PageHeading({ actions, description, title }: { actions?: ReactNode; description?: string; title: string }) {
  return (
    <header className="page-heading">
      <div>
        <h1>{title}</h1>
        {description ? <p>{description}</p> : null}
      </div>
      {actions ? <div className="page-actions">{actions}</div> : null}
    </header>
  );
}
