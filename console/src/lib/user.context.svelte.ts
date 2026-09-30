/**
 * User-level context for session identity and a few user-scoped extras.
 *
 * `UserState` holds the authenticated user's identity (from better-auth,
 * hydrated in `hooks.server.ts`) plus small persisted extras (`locale`,
 * `packageManager`). There is no appearance/theme system in this console
 * yet -- an earlier draft of this file coupled `UserState` to a
 * `ModeWatcherConfiguration` from a shadcn-svelte "registry/blocks" layout
 * that was never added here (`$lib/registry/blocks/...` doesn't exist in
 * this project), so that coupling was dropped rather than left unbuilt. If
 * a real appearance/theme block gets added later, this can grow back to
 * merge with it.
 *
 * The `locale` preference stores the user's chosen Paraglide locale.
 * When set, returning users can be auto-redirected to their language.
 * The actual navigation is left to the consuming component (via
 * `goto(site.localizeHref(path, { locale }))`).
 *
 * @example
 * ```ts
 * // In a layout — create and provide
 * import { UserContext, UserState } from "./user.context.svelte";
 * UserContext.set(new UserState(data.user));
 *
 * // In a component — consume
 * const user = UserContext.get();
 * user.isAuthenticated;        // reactive
 * user.displayName;            // reactive
 * ```
 */
import { Context, PersistedState } from "runed";

/** Local stand-in for a package-manager preference; not tied to any
 * external registry block. */
export type PackageManager = "npm" | "pnpm" | "yarn" | "bun";

// ─── Types ───────────────────────────────────────────────────────────────────

/**
 * Authenticated user identity (mirrors `App.Locals["user"]` from better-auth).
 *
 * The shape matches better-auth's user object with admin plugin fields.
 */
export interface UserIdentity {
	id: string;
	/** Display name. */
	name: string;
	/** User email address. */
	email: string;
	/** Whether the email has been verified. */
	emailVerified?: boolean;
	/** URL to the user's avatar/profile image. */
	image?: string | null;
	/** User role (from admin plugin). */
	role?: string | null;
	createdAt?: Date;
	updatedAt?: Date;
}

/**
 * User-scoped extras, independent of any appearance/theme system.
 *
 * `locale` stores the user's preferred Paraglide locale (e.g. `"en"`,
 * `"es"`). When set, it is persisted in `localStorage` so returning
 * users can be redirected to their preferred language automatically.
 */
export interface ExtraPreferences {
	packageManager: PackageManager;
	/**
	 * The user's preferred locale code (e.g. `"en"`, `"es"`).
	 *
	 * A value of `null` means "use the site / browser default".
	 */
	locale: string | null;
}

// ─── Constants ───────────────────────────────────────────────────────────────

const USER_EXTRA_PREFS_KEY = "user-extra-prefs";

const DEFAULT_EXTRA: ExtraPreferences = {
	packageManager: "pnpm" as PackageManager,
	locale: null,
};

// ─── State class ─────────────────────────────────────────────────────────────

export class UserState {
	// ── Backing state ───────────────────────────────────────────────────────
	#identity = $state<UserIdentity | null>(null);
	readonly #extra: PersistedState<ExtraPreferences>;

	constructor(identity?: UserIdentity | null) {
		this.#identity = identity ?? null;
		this.#extra = new PersistedState<ExtraPreferences>(
			USER_EXTRA_PREFS_KEY,
			DEFAULT_EXTRA,
			{ storage: "local" },
		);
	}

	// ── Identity ────────────────────────────────────────────────────────────

	/** The authenticated user, or `null` when anonymous. */
	get user(): UserIdentity | null {
		return this.#identity;
	}

	/** Reactive boolean — `true` when the user has a valid session. */
	isAuthenticated: boolean = $derived.by(() => this.#identity !== null);

	/** Display name (from better-auth `name` field), or `null` when anonymous. */
	displayName: string | null = $derived.by(() => this.#identity?.name ?? null);

	get displayNameFallback(): string {
		return this.displayName ?? "Guest";
	}
	/** User display handle (e.g. `@jason`), or `null`. */
	displayHandle: string = $derived.by(() => `@${this.displayName ?? ""}`);

	/** User email, or `null` when anonymous. */
	email: string | null = $derived.by(() => this.#identity?.email ?? null);

	get emailFallback(): string {
		return this.email ?? "";
	}

	/** Avatar image URL (from better-auth `image` field), or `null`. */
	avatarUrl: string | null = $derived.by(() => this.#identity?.image ?? null);

	/** User role (from admin plugin), or `null`. */
	role: string | null = $derived.by(() => this.#identity?.role ?? null);

	/** Whether the current user has the admin role. */
	isAdmin: boolean = $derived.by(() => this.#identity?.role === "admin");

	/** Initials for avatar fallback (first two characters of the display name, uppercased). */
	initials: string = $derived.by(() => {
		const name = this.#identity?.name;
		if (!name) return "?";
		return name
			.split(" ")
			.slice(0, 2)
			.map((word) => word[0])
			.join("")
			.toUpperCase();
	});

	/**
	 * Set the authenticated user identity.
	 *
	 * Typically called when the session is hydrated from the server
	 * (e.g. from `$page.data.user` populated by `hooks.server.ts`).
	 */
	login = (identity: UserIdentity): void => {
		this.#identity = identity;
	};

	/** Clear the user identity (logout). */
	logout = (): void => {
		this.#identity = null;
	};

	// ── Extras (packageManager, locale) ─────────────────────────────────────

	/** The current extras, persisted to `localStorage`. */
	current: ExtraPreferences = $derived.by(() => this.#extra.current);

	/** Update one or more extra preference fields. */
	setConfig = (data: Partial<ExtraPreferences>): void => {
		this.#extra.current = { ...this.#extra.current, ...data };
	};

	/** Shortcut — set the preferred package manager. */
	setPackageManager = (pm: PackageManager): void => {
		this.#extra.current = { ...this.#extra.current, packageManager: pm };
	};

	// ── i18n / Locale ───────────────────────────────────────────────────────

	/**
	 * The user's preferred locale, or `null` if they haven't chosen one.
	 *
	 * When `null`, the site / browser default locale should be used.
	 * Components can check this to decide whether to redirect on load:
	 *
	 * ```ts
	 * const user = UserContext.get();
	 * if (user.locale) {
	 *   goto(site.localizeHref(page.url.pathname, { locale: user.locale }));
	 * }
	 * ```
	 */
	locale: string | null = $derived.by(() => this.#extra.current.locale);

	/**
	 * Convenience boolean — `true` when the user has explicitly chosen a locale.
	 */
	hasLocalePreference: boolean = $derived.by(
		() => this.#extra.current.locale !== null,
	);

	/**
	 * Persist the user's preferred locale.
	 *
	 * This only updates the stored preference — the actual locale switch
	 * (URL navigation) must be performed by the calling component using
	 * `goto(site.localizeHref(path, { locale }))`.
	 *
	 * Pass `null` to clear the preference (revert to site default).
	 */
	setLocale = (locale: string | null): void => {
		this.#extra.current = { ...this.#extra.current, locale };
	};
}

// ─── Runed Context ───────────────────────────────────────────────────────────

export const UserContext = new Context<UserState>("user-context");
