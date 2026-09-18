import type { IconProps } from "@lucide/svelte";
import type { Component, ComponentProps, Snippet } from "svelte";
import type {
	RenderComponentConfig,
	RenderSnippetConfig,
} from "$lib/components/ui/data-table/render-helpers";

/**
 * @name Mandatory
 * @description Returns a type with the properties of T required
 * @type T
 * @param T, type to make required
 * @param K, keys to make required
 * @returns {T & { [P in K]-?: T[P] }} type with the properties of T required
 */
export type Mandatory<T, K extends keyof T> = Required<Pick<T, K>> & Omit<T, K>;

/**
 * @name getProperty
 * @description keyof T returns a union of string literal types. The extends keyword is used to apply constraints to K, so that K is one of the string literal types only
 * extends means “is assignable” instead of “inherits”; K extends keyof T means that any value of type K can be assigned to the string literal union types
 * The indexed access operator obj[key] returns the same type that the property has in the object
 * @type T @typeof object
 * @type K, {PropertyKey} `extends keyof` object
 * @param obj {T}, object to get property from
 * @param key {K}, key of object to get
 * @returns {T[K]} key in arbitrary object of T
 */
export const getProperty = <T, K extends keyof T>(obj: T, key: K): T[K] => {
	return obj[key];
};

//? https://refine.dev/blog/typescript-mapped-types/#typescript-type-mapper-utility-vs-ts-mapped-type-the-difference
/**
 * Makes a type nullable.
 */
export type Nullable<T> = T | null;

/**
 * Makes a type optional/undefined.
 */
export type Optional<T> = T | undefined;

/**
 * Allows a type to be either present, null, or undefined.
 */
export type Maybe<T> = T | null | undefined;

/**
 * Allows a value to be either a single item, an array of items, null, or undefined.
 */
export type MaybeArray<T> = T | T[] | null | undefined;

/**
 * Allows a tuple/parameter-list type to be present, null, or undefined.
 */
export type MaybeParams<T extends unknown[] = unknown[]> = T | null | undefined;

/**
 * @name NoInfer
 * @description Returns the type of the argument without inferring it
 * @type T
 * @param T, type to remove inference from
 * @returns {T} type without inference
 */
export type NoInfer<A> = [A][A extends unknown ? 0 : never]; // [A][A extends any ? 0 : never];

/**
 * @name GenericItem
 * @description Returns the type of the argument without inferring it
 * @type T
 * @param T, type to remove inference from
 * @returns {T} type without inference
 */

// biome-ignore lint/suspicious/noExplicitAny: svelte component props
export type GenericItem = { component: Component; props?: Record<string, any> };

/**
 * @name GenericSelectorOption
 * @description Returns the type of the argument without inferring it
 * @type T
 * @param T, type to remove inference from
 * @returns {T} type without inference
 */
export type GenericSelectorOption = {
	label: string;
	value: string;
	icon?: Component<IconProps>;
};

/**
 * @name GenericViewableContent
 * @description Returns the type of the argument without inferring it
 * @type T
 * @param T, type to remove inference from
 * @returns {T} type without inference
 */
export type GenericViewableContent =
	| string
	| Snippet
	| InstanceType<typeof RenderSnippetConfig>
	| InstanceType<typeof RenderComponentConfig>;

/**
 * @name ExtractGenericViewableContent
 * @description Returns the type of the argument without inferring it
 * @type T
 * @param T, type to remove inference from
 * @returns {T} type without inference
 * @example
 * ```svelte
 * <script lang="ts">
 *		import type { ExtractGenericViewableContent, GenericViewableContent } from "$lib/utilities/generics";
 *		import type { PrimitiveDivAttributes } from "$lib/utils";
 *		import { GenericRenderer } from "$lib/registry/ui/generic-renderer/index.ts";
 *		type $$Props = {
 *			readonly id: string;
 *			actions?: ExtractGenericViewableContent<GenericViewableContent>;
 *			view: ExtractGenericViewableContent<GenericViewableContent>;
 *		} & PrimitiveDivAttributes;
 *		let { id, actions, view, ...rest }: $$Props = $props();
 * </script>
 * <div {id} {...rest}>
 * <GenericRenderer {view} />
 *		{#if actions}
 *			<GenericRenderer {actions} />
 *		{/if}
 * </div>
 * ```
 */
export type ExtractGenericViewableContent<T = GenericViewableContent> =
	T extends string
		? string
		: T extends RenderSnippetConfig<infer TProps>
			? TProps
			: T extends RenderComponentConfig<infer TComponent>
				? NoInfer<TComponent>
				: T extends Snippet<[infer TProps]>
					? TProps
					: never;

/**
 * @name RecordEntries
 * @description Returns an array of entries for a record
 * @type K extends string, V
 * @param K {string}, key type
 * @param V, value type
 */
export type RecordEntries<K extends string, V> = Record<K, V>[];

/**
 * @name RecordTuple
 * @description Returns a tuple of a key and a value
 * @type K extends string, V
 * @param K {string}, key type
 * @param V, value type
 */
export type RecordTuple<K extends string, V> = [K, V];

/**
 * @name InputFn
 * @description Returns a function that takes any number of arguments and returns any type
 * @see https://www.jpwilliams.dev/how-to-unpack-the-return-type-of-a-promise-in-typescript
 * @type T extends InputFn
 * @param T, function type
 */
export type InputFn = (...args: unknown[]) => unknown;

/**
 * @name AsyncReturnType
 * @description Returns the return type of a function
 * @see https://www.jpwilliams.dev/how-to-unpack-the-return-type-of-a-promise-in-typescript
 * @type T extends InputFn
 * @param T, function type
 */
export type AsyncReturnType<T extends InputFn> =
	// if T matches this signature and returns a Promise, extract
	// U (the type of the resolved promise) and use that, or...
	T extends (...args: unknown[]) => Promise<infer U>
		? U
		: // if T matches this signature and returns anything else,
			// extract the return value U and use that, or...
			T extends (...args: unknown[]) => infer U
			? U
			: // if everything goes to hell, return an `any`
				unknown;

/**
 * @name Unwrap
 * @description Returns the return type of a function
 * @see https://www.jpwilliams.dev/how-to-unpack-the-return-type-of-a-promise-in-typescript
 * @type T
 * @param T, function type
 */
export type Unwrap<T> =
	T extends Promise<infer U>
		? U
		: T extends (...args: unknown[]) => Promise<infer U>
			? U
			: T extends (...args: unknown[]) => infer U
				? U
				: T;

/**
 * @name Expand
 * @description `infer U` is used to extract the type of the argument without inferring it. `{ [K in keyof U]: U[K] }` is used to expand the type of the argument to a declarative type.
 * @type T
 * @param T, type to remove inference from
 * @returns {T} type expanded to a declarative type
 */
export type Expand<T> = T extends infer U ? { [K in keyof U]: U[K] } : never;

/**
 * The props that the component accepts.
 */
export interface IProps extends Record<PropertyKey, unknown> {}

/**
 * @name InheritedSnippetProps
 * @description Returns a snippet with the props of the type T
 * @type T
 * @param T, type to add the props to
 * @returns {Snippet<[{ props: T }]> | Snippet<[T & { props: T }]>} snippet with the props of the type T
 * @example
 * ```svelte
 * <script lang="ts">
 *		import type { InheritedSnippetProps } from "$lib/utilities/generics";
 *		type $$Props = {
 *			readonly id: string;
 *			actions?: InheritedSnippetProps<{ readonly id: string }>;
 *		} & PrimitiveDivAttributes;
 *		let { id, actions, ...rest }: $$Props = $props();
 * </script>
 * <div {id} {...rest}>
 *		{@render actions?.({ props: { id } })}
 * </div>
 * ```
 */
export type InheritedSnippetProps<
	T extends Record<string, unknown> = { _default: never },
> = T extends { _default: never } ? Snippet : Snippet<[T | (T & { props: T })]>;
/**
 * Shared snippet container shape used by generic renderer wrappers.
 */
export type GenericSnippetProps = InheritedSnippetProps<IProps>;

/**
 * Snippet props bound to a specific Svelte component's props.
 */
export type SnippetProps<T extends Component> = {
	[key: string]: Maybe<unknown>;
	props?: Maybe<Expand<ComponentProps<T>>>;
};

/**
 * Snippet params bound to a specific Svelte component's props.
 */
export type SnippetParams<T extends Component> = [SnippetProps<T>];

/**
 * @name StyleProperties
 * @see https://github.com/huntabyte/bits-ui/blob/d93334afd6c2ccac82fde39215fbf5abd8be52c9/packages/bits-ui/src/lib/shared/index.ts#L29
 * @see https://github.com/frenic/csstype/blob/ab21aaa8eef61bc8e6cee162994cf7e85fd54686/typings/mdn-data.d.ts#L17
 * @description Returns a type with the properties of the child snippet
 * @type StylePropertyMap
 * @param StylePropertyMap, type to add the child snippet to
 * @returns {StylePropertyMap & { [str: `--${string}`]: any; }} type with the properties of the child snippet
 */
export type StyleProperties = StylePropertyMap & {
	// Allow any CSS Custom Properties
	// biome-ignore lint/suspicious/noExplicitAny: biome is not able to infer the type of the CSS Custom Properties
	[str: `--${string}`]: any;
};

/**
 * @name WithChild
 * @see https://github.com/huntabyte/bits-ui/blob/d93334afd6c2ccac82fde39215fbf5abd8be52c9/packages/bits-ui/src/lib/internal/types.ts#L11
 * @description Returns a type with the properties of T and the properties of the child snippet
 * @type T
 * @param T, type to add the child snippet to
 * @param SnippetProps, type to add the child snippet to
 * @param Ref, type to add the child snippet to
 * @returns {T & { child?: Snippet<[{ props: Record<string, unknown> }]> | Snippet<[SnippetProps & { props: Record<string, unknown> }]>; children?: SnippetProps extends { _default: never } ? Snippet : Snippet<[SnippetProps]>; style?: StyleProperties | string | null | undefined; ref?: Ref | null | undefined; }} type with the properties of T and the properties of the child snippet
 */
export type WithChild<
	/**
	 * The props that the component accepts.
	 * @alias IProps
	 */
	Props extends Record<PropertyKey, unknown> = IProps,
	/**
	 * The props that are passed to the `child` and `children` snippets. The `ElementProps` or `ComponentProps` are
	 * merged with these props for the `child` snippet.
	 * @alias ISnippetProps
	 */
	SnippetProps extends Record<PropertyKey, unknown> = { _default: never },
	/**
	 * The underlying DOM element being rendered. You can bind to this prop to
	 * programmatically interact with the element.
	 */
	Ref = HTMLElement,
> = Omit<Props, "child" | "children"> & {
	child?: SnippetProps extends { _default: never }
		? Snippet<[{ props: Record<string, unknown> }]>
		: Snippet<[SnippetProps & { props: Record<string, unknown> }]>;
	children?: SnippetProps extends { _default: never }
		? Snippet
		: Snippet<[SnippetProps]>;
	style?: StyleProperties | string | null | undefined;
	ref?: Ref | null | undefined;
};

/**
 * Adds a `ref` property to a type.
 * @type T
 * @param T, type to add the `ref` property to
 * @param U, type of the `ref` property
 * @returns {T & { ref?: U | null; }} type with the `ref` property
 */

export type WithElementRef<T, U extends HTMLElement = HTMLElement> = T & {
	ref?: U | null;
};

/**
 * @type WithoutElementRef
 * @template T
 * @description Removes a `ref` property from a type when it exists.
 */
export type WithoutElementRef<
	T,
	U extends HTMLElement = HTMLElement,
> = T extends {
	ref?: U | null;
}
	? Omit<T, "ref">
	: T;

/**
 * @type WithoutElementAttributes
 * @template T - The type to remove `attributes` from.
 * @description Removes an `attributes` property from a type when it exists.
 */
export type WithoutElementAttributes<
	T,
	U extends HTMLElement = HTMLElement,
> = T extends {
	attributes?: U | null;
}
	? Omit<T, "attributes">
	: T;

/**
 * @type WithoutChildrenOrChild
 * @template T - The type to remove `children` and `child` props from.
 * @description Removes both `children` and `child` props from T.
 */
export type WithoutChildrenOrChild<T> = WithoutChildren<WithoutChild<T>>;

/**
 * @type WithoutChildren
 * @template T - The type to remove the `children` snippet prop from.
 * @description Removes the `children` snippet prop from T when present.
 */
export type WithoutChildren<T> = T extends {
	children?: unknown;
}
	? Omit<T, "children">
	: T;

/**
 * @type WithoutChild
 * @template T - The type to remove the `child` snippet prop from.
 * @description Removes the `child` snippet prop from T when present.
 */
export type WithoutChild<T> = T extends {
	child?: unknown;
}
	? Omit<T, "child">
	: T;
