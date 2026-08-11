export function getApiBaseUrl(): URL {
  const configuredUrl = process.env.LEDGER_API_BASE_URL;

  if (!configuredUrl) {
    throw new Error("LEDGER_API_BASE_URL is not configured.");
  }

  let url: URL;
  try {
    url = new URL(configuredUrl);
  } catch {
    throw new Error("LEDGER_API_BASE_URL must be a valid absolute URL.");
  }

  if (!['http:', 'https:'].includes(url.protocol)) {
    throw new Error("LEDGER_API_BASE_URL must use HTTP or HTTPS.");
  }

  if (url.username || url.password || url.search || url.hash) {
    throw new Error(
      "LEDGER_API_BASE_URL must not contain credentials, query parameters, or a fragment.",
    );
  }

  url.pathname = `${url.pathname.replace(/\/$/, "")}/`;
  return url;
}
