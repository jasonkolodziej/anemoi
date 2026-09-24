import { writable } from "svelte/store";

export const waiterLoading = writable(false);

let inflight = 0;

export function setWaiterLoading(loading: boolean) {
  if (loading) {
    inflight += 1;
  } else {
    inflight = Math.max(inflight - 1, 0);
  }
  waiterLoading.set(inflight > 0);
}

export async function withWaiterLoading<T>(task: () => Promise<T>): Promise<T> {
  setWaiterLoading(true);
  try {
    return await task();
  } finally {
    setWaiterLoading(false);
  }
}
