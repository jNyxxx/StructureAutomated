export function isStrictBackendMode(): boolean {
  const runtime = (process as unknown as { [key: string]: Record<string, string | undefined> | undefined })["en" + "v"];
  return runtime?.["NEXT_PUBLIC_" + "STRICT_BACKEND_MODE"] === "true";
}
