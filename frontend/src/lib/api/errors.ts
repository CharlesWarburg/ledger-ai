export interface ApiValidationIssue {
  loc?: Array<string | number>;
  msg?: string;
  type?: string;
}

interface FastApiErrorBody {
  detail?: string | ApiValidationIssue[];
}

export class ApiError extends Error {
  readonly status: number;
  readonly issues: ApiValidationIssue[];
  readonly body: unknown;

  constructor(
    message: string,
    options: { status: number; issues?: ApiValidationIssue[]; body?: unknown },
  ) {
    super(message);
    this.name = "ApiError";
    this.status = options.status;
    this.issues = options.issues ?? [];
    this.body = options.body;
  }
}

function isValidationIssue(value: unknown): value is ApiValidationIssue {
  return typeof value === "object" && value !== null && "msg" in value;
}

export function getApiErrorMessage(status: number, body: unknown): string {
  if (typeof body === "object" && body !== null && "detail" in body) {
    const { detail } = body as FastApiErrorBody;

    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }

    if (Array.isArray(detail)) {
      const messages = detail
        .filter(isValidationIssue)
        .map((issue) => issue.msg)
        .filter((message): message is string => Boolean(message));

      if (messages.length > 0) {
        return messages.join(" ");
      }
    }
  }

  if (typeof body === "string" && body.trim()) {
    return body;
  }

  return `Request failed with status ${status}.`;
}

export function getValidationIssues(body: unknown): ApiValidationIssue[] {
  if (typeof body !== "object" || body === null || !("detail" in body)) {
    return [];
  }

  const detail = (body as FastApiErrorBody).detail;
  return Array.isArray(detail) ? detail.filter(isValidationIssue) : [];
}
