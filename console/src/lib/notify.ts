import { toast } from 'svelte-sonner';
import { ApiError } from '$lib/api/client';

/** The API's own message for a failed call: `404: no such storm`. */
export function errorDetail(e: unknown): string {
	if (e instanceof ApiError) return `${e.status}: ${e.message}`;
	return e instanceof Error ? e.message : String(e);
}

/**
 * A failure the person should see, as a toast (`<Toaster />` in
 * +layout.svelte) rather than a banner in the page: `title` says what
 * failed, the description is the API's message. With `retry`, the toast
 * offers to try again and stays up longer. The title is also the toast's
 * id, so a repeated failure updates one toast instead of stacking.
 */
export function notifyError(title: string, e: unknown, retry?: () => void): void {
	toast.error(title, {
		id: title,
		description: errorDetail(e),
		duration: retry ? 12_000 : 6_000,
		action: retry ? { label: 'Retry', onClick: retry } : undefined
	});
}
