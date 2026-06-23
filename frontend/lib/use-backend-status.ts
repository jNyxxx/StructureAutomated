"use client";

import { useEffect, useState } from "react";

import { fetchReady, mapBackendErrorToStatus, mapHealthResponseToStatus, type BackendStatusView } from "./backend-api";

const initialStatus: BackendStatusView = {
  state: "unknown",
  label: "Checking backend",
  message: "Checking local backend readiness. This does not imply production approval.",
  requestId: null,
  correlationId: null,
  rawStatus: null,
};

export function useBackendReadyStatus(): BackendStatusView {
  const [status, setStatus] = useState<BackendStatusView>(initialStatus);

  useEffect(() => {
    let active = true;

    fetchReady()
      .then((response) => {
        if (active) setStatus(mapHealthResponseToStatus(response, "ready"));
      })
      .catch((error: unknown) => {
        if (active) setStatus(mapBackendErrorToStatus(error, "ready"));
      });

    return () => {
      active = false;
    };
  }, []);

  return status;
}
