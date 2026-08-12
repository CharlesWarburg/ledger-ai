import "server-only";

import { getApiBaseUrl } from "@/lib/api/config";
import { ApiError, getApiErrorMessage, getValidationIssues } from "@/lib/api/errors";
import type {
  AccessTokenResponse,
  UserLogin,
  UserRegister,
  UserResponse,
} from "@/lib/api/types";

async function readBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return response.json();
  }

  const text = await response.text();
  return text || undefined;
}

async function backendRequest<T>(
  path: string,
  init: RequestInit,
): Promise<T> {
  const response = await fetch(new URL(path.replace(/^\//, ""), getApiBaseUrl()), {
    ...init,
    cache: "no-store",
  });
  const body = await readBody(response);

  if (!response.ok) {
    throw new ApiError(getApiErrorMessage(response.status, body), {
      status: response.status,
      issues: getValidationIssues(body),
      body,
    });
  }

  return body as T;
}

function jsonRequest(body: object): RequestInit {
  return {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  };
}

export function login(credentials: UserLogin): Promise<AccessTokenResponse> {
  return backendRequest<AccessTokenResponse>(
    "/auth/login",
    jsonRequest(credentials),
  );
}

export function register(registration: UserRegister): Promise<UserResponse> {
  return backendRequest<UserResponse>(
    "/auth/register",
    jsonRequest(registration),
  );
}

export function getCurrentUser(token: string): Promise<UserResponse> {
  return backendRequest<UserResponse>("/auth/me", {
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${token}`,
    },
  });
}
