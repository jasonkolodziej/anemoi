import { writable } from "svelte/store";

export const waiterLoading = writable(false);

export function setWaiterLoading(loading: boolean) {
  waiterLoading.set(loading);
}

export async function withWaiterLoading<T>(task: () => Promise<T>): Promise<T> {
  setWaiterLoading(true);
  try {
    return await task();
  } finally {
    setWaiterLoading(false);
  }
}
