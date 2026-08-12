"use client";

import { useEffect } from "react";

export default function WorkspaceError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="state-card error-state">
      <div className="state-icon">!</div>
      <h2>Something went wrong</h2>
      <p>We couldn’t load this page. Your data is safe, and you can try again.</p>
      <button className="button" onClick={reset} type="button">Try again</button>
    </div>
  );
}
