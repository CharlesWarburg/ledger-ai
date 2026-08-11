import { getApiBaseUrl } from "@/lib/api/config";

const ALLOWED_ROUTE_ROOTS = new Set([
  "assistant",
  "auth",
  "customers",
  "dashboard",
  "db-health",
  "documents",
  "health",
  "insights",
  "invoices",
  "payments",
  "reports",
]);

const REQUEST_HEADERS = ["accept", "authorization", "content-type"];
const RESPONSE_HEADERS = [
  "cache-control",
  "content-disposition",
  "content-length",
  "content-type",
  "www-authenticate",
];

function jsonError(message: string, status: number): Response {
  return Response.json({ detail: message }, { status });
}

async function proxyRequest(
  request: Request,
  context: { params: Promise<{ path: string[] }> },
): Promise<Response> {
  const { path } = await context.params;

  if (!path.length || !ALLOWED_ROUTE_ROOTS.has(path[0])) {
    return jsonError("Unknown API route", 404);
  }

  const sourceUrl = new URL(request.url);
  let targetUrl: URL;

  try {
    targetUrl = new URL(path.map(encodeURIComponent).join("/"), getApiBaseUrl());
    targetUrl.search = sourceUrl.search;
  } catch {
    return jsonError("Frontend API proxy is not configured", 500);
  }

  const headers = new Headers();
  for (const name of REQUEST_HEADERS) {
    const value = request.headers.get(name);
    if (value) {
      headers.set(name, value);
    }
  }

  try {
    const response = await fetch(targetUrl, {
      method: request.method,
      headers,
      body:
        request.method === "GET" || request.method === "HEAD"
          ? undefined
          : await request.arrayBuffer(),
      cache: "no-store",
      redirect: "manual",
    });

    const responseHeaders = new Headers();
    for (const name of RESPONSE_HEADERS) {
      const value = response.headers.get(name);
      if (value) {
        responseHeaders.set(name, value);
      }
    }

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch {
    return jsonError("Backend API is unavailable", 502);
  }
}

export const dynamic = "force-dynamic";

export const GET = proxyRequest;
export const POST = proxyRequest;
export const PUT = proxyRequest;
export const PATCH = proxyRequest;
export const DELETE = proxyRequest;
export const HEAD = proxyRequest;
