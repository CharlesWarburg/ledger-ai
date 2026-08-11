import { ApiError, getApiErrorMessage, getValidationIssues } from "./errors";

const API_PROXY_PATH = "/api/backend";

type QueryValue = string | number | boolean | null | undefined;

export interface ApiRequestOptions
  extends Omit<RequestInit, "body" | "headers"> {
  body?: BodyInit | object | null;
  headers?: HeadersInit;
  query?: Record<string, QueryValue>;
  token?: string | null;
}

function createRequestUrl(
  path: string,
  query?: Record<string, QueryValue>,
): string {
  if (!path.startsWith("/") || path.startsWith("//")) {
    throw new Error("API paths must start with a single forward slash.");
  }

  const url = new URL(`${API_PROXY_PATH}${path}`, "http://ledger.local");

  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null) {
      url.searchParams.set(key, String(value));
    }
  }

  return `${url.pathname}${url.search}`;
}

function prepareBody(
  body: ApiRequestOptions["body"],
  headers: Headers,
): BodyInit | null | undefined {
  if (
    body === undefined ||
    body === null ||
    typeof body === "string" ||
    body instanceof FormData ||
    body instanceof URLSearchParams ||
    body instanceof Blob ||
    body instanceof ArrayBuffer ||
    ArrayBuffer.isView(body)
  ) {
    return body as BodyInit | null | undefined;
  }

  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  return JSON.stringify(body);
}

async function readResponseBody(response: Response): Promise<unknown> {
  if (response.status === 204) {
    return undefined;
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return response.json();
  }

  const text = await response.text();
  return text || undefined;
}

export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const { body, headers: initialHeaders, query, token, ...requestInit } = options;
  const headers = new Headers(initialHeaders);

  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(createRequestUrl(path, query), {
    ...requestInit,
    body: prepareBody(body, headers),
    headers,
  });
  const responseBody = await readResponseBody(response);

  if (!response.ok) {
    throw new ApiError(getApiErrorMessage(response.status, responseBody), {
      status: response.status,
      issues: getValidationIssues(responseBody),
      body: responseBody,
    });
  }

  return responseBody as T;
}

export async function apiDownload(
  path: string,
  options: Omit<ApiRequestOptions, "body"> = {},
): Promise<Response> {
  const { headers: initialHeaders, query, token, ...requestInit } = options;
  const headers = new Headers(initialHeaders);

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(createRequestUrl(path, query), {
    ...requestInit,
    headers,
  });

  if (!response.ok) {
    const responseBody = await readResponseBody(response);
    throw new ApiError(getApiErrorMessage(response.status, responseBody), {
      status: response.status,
      issues: getValidationIssues(responseBody),
      body: responseBody,
    });
  }

  return response;
}
