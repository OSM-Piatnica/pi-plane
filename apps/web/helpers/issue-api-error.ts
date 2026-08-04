export const getIssueApiErrorMessage = (error: unknown, fallback: string): string => {
  if (!error) return fallback;
  if (typeof error === "string" && error.trim()) return error;

  if (typeof error === "object") {
    const payload = error as Record<string, unknown>;

    if (typeof payload.error === "string" && payload.error.trim()) return payload.error;
    if (typeof payload.message === "string" && payload.message.trim()) return payload.message;

    const nonFieldErrors = payload.non_field_errors;
    if (Array.isArray(nonFieldErrors) && nonFieldErrors.length > 0) {
      const first = nonFieldErrors[0];
      if (typeof first === "string" && first.trim()) return first;
    }

    for (const value of Object.values(payload)) {
      if (typeof value === "string" && value.trim()) return value;
      if (Array.isArray(value) && typeof value[0] === "string" && value[0].trim()) return value[0];
    }
  }

  return fallback;
};
