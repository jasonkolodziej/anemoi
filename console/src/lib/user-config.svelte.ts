/**
 * Re-exports `UserContext` as `UserConfigContext` for backwards
 * compatibility, bridging to the canonical `UserContext`/`UserState` in
 * `$lib/user.context.svelte`. No appearance/theme fields (`layout`, etc.)
 * -- that coupling was dropped from `UserState` (#171; no mode-watcher
 * block exists in this console). `current` is just the small persisted
 * extras.
 *
 * @example
 * ```ts
 * import { UserConfigContext } from "$lib/user-config.svelte";
 * const userConfig = UserConfigContext.get();
 * userConfig.current.packageManager; // "pnpm" | "npm" | …
 * userConfig.setConfig({ packageManager: "npm" });
 * ```
 */

export type {
	ExtraPreferences,
	PackageManager,
	UserIdentity,
} from "$lib/user.context.svelte";
export {
	UserContext as UserConfigContext,
	UserState as UserConfig,
} from "$lib/user.context.svelte";
