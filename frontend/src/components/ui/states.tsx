import type { ReactNode } from "react";

export function EmptyState({ action, description, title }: { action?: ReactNode; description: string; title: string }) {
  return <div className="state-card"><div className="state-icon">+</div><h2>{title}</h2><p>{description}</p>{action}</div>;
}

export function ErrorState({ description = "We couldn’t load this information. Try again in a moment.", title = "Something went wrong" }: { description?: string; title?: string }) {
  return <div className="state-card error-state"><div className="state-icon">!</div><h2>{title}</h2><p>{description}</p></div>;
}

export function LoadingState() {
  return <div aria-label="Loading" className="loading-grid" role="status">{Array.from({ length: 4 }).map((_, index) => <div className="skeleton-card" key={index}><span /><span /><span /></div>)}</div>;
}
