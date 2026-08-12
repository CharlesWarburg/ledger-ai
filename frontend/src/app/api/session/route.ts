import { ApiError } from "@/lib/api/errors";
import type { UserLogin } from "@/lib/api/types";
import { getCurrentUser, login } from "@/lib/auth/backend";
import { createSession, deleteSession, getSessionToken } from "@/lib/auth/session";

function jsonError(detail: string, status: number): Response {
  return Response.json({ detail }, { status });
}

function credentialsFrom(value: unknown): UserLogin | null {
  if (typeof value !== "object" || value === null) {
    return null;
  }

  const email = "email" in value ? value.email : null;
  const password = "password" in value ? value.password : null;

  if (typeof email !== "string" || typeof password !== "string") {
    return null;
  }

  return { email: email.trim().toLowerCase(), password };
}

export async function GET(): Promise<Response> {
  const token = await getSessionToken();
  if (!token) {
    return jsonError("Not authenticated", 401);
  }

  try {
    return Response.json(await getCurrentUser(token));
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      await deleteSession();
    }
    return jsonError("Session is no longer valid", 401);
  }
}

export async function POST(request: Request): Promise<Response> {
  let credentials: UserLogin | null = null;
  try {
    credentials = credentialsFrom(await request.json());
  } catch {
    // Invalid JSON is handled as invalid credentials below.
  }

  if (!credentials || !credentials.email || !credentials.password) {
    return jsonError("Email and password are required", 422);
  }

  try {
    const token = await login(credentials);
    await createSession(token.access_token, token.expires_in);
    return Response.json(await getCurrentUser(token.access_token));
  } catch (error) {
    if (error instanceof ApiError) {
      return Response.json(error.body ?? { detail: error.message }, {
        status: error.status,
      });
    }
    return jsonError("Authentication service is unavailable", 502);
  }
}

export async function DELETE(): Promise<Response> {
  await deleteSession();
  return new Response(null, { status: 204 });
}
