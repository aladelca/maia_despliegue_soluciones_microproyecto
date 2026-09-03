import { afterEach, expect, it, vi } from "vitest";

import { API_REQUEST_TIMEOUT_MS, getModelMetadata } from "./api";

afterEach(() => {
  vi.restoreAllMocks();
});

it("allows enough time for a cold Lambda metadata request", async () => {
  const signal = new AbortController().signal;
  const timeout = vi.spyOn(AbortSignal, "timeout").mockReturnValue(signal);
  vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok: true,
    json: async () => ({
      model_version: "champion-v1",
      feature_names: ["Administrative"],
      threshold: 0.56,
      validation_metrics: {},
      test_metrics: {},
    }),
  } as Response);

  await expect(getModelMetadata()).resolves.toMatchObject({ model_version: "champion-v1" });
  expect(timeout).toHaveBeenCalledWith(29_000);
  expect(API_REQUEST_TIMEOUT_MS).toBe(29_000);
});
