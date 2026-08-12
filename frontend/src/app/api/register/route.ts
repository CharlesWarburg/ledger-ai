import { ApiError } from "@/lib/api/errors";
import type { UserRegister } from "@/lib/api/types";
import { getCurrentUser, login, register } from "@/lib/auth/backend";
import { createSession } from "@/lib/auth/session";

function jsonError(detail: string, status: number): Response {
  return Response.json({ detail }, { status });
}

function registrationFrom(value: unknown): UserRegister | null {
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

export async function POST(request: Request): Promise<Response> {
  let registration: UserRegister | null = null;
  try {
    registration = registrationFrom(await request.json());
  } catch {
    // Invalid JSON is handled as invalid registration data below.
  }

  if (!registration || !registration.email || registration.password.length < 8) {
    return jsonError("Enter a valid email and a password of at least 8 characters", 422);
  }

  try {
    await register(registration);
    const token = await login(registration);
    await createSession(token.access_token, token.expires_in);
    return Response.json(await getCurrentUser(token.access_token), { status: 201 });
  } catch (error) {
    if (error instanceof ApiError) {
      return Response.json(error.body ?? { detail: error.message }, {
        status: error.status,
      });
    }
    return jsonError("Registration service is unavailable", 502);
  }
}
