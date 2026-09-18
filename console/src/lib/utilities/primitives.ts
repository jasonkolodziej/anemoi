import type {
	HTMLAnchorAttributes,
	HTMLAttributes,
	HTMLButtonAttributes,
	HTMLImgAttributes,
	HTMLInputAttributes,
	HTMLLabelAttributes,
	HTMLLiAttributes,
	HTMLOlAttributes,
	HTMLTableAttributes,
	HTMLTdAttributes,
	HTMLTextareaAttributes,
	HTMLThAttributes,
	SVGAttributes,
	MouseEventHandler,
} from "svelte/elements";
import type { WithElementRef } from "$lib/utilities/generics";

// Wrappers around svelte's `HTMLAttributes` types to add a `ref` prop can be bound to
// to get a reference to the underlying DOM element the component is rendering.
export type PrimitiveDivAttributes = WithElementRef<
	HTMLAttributes<HTMLDivElement>
>;
export type PrimitiveSectionAttributes = WithElementRef<
	HTMLAttributes<HTMLOptionElement>
>;
export type PrimitiveElementAttributes = WithElementRef<
	HTMLAttributes<HTMLElement>
>;
export type PrimitiveFormAttributes = WithElementRef<
	HTMLAttributes<HTMLFormElement>
>;
export type PrimitiveAnchorAttributes = WithElementRef<HTMLAnchorAttributes>;
export type PrimitiveButtonAttributes = WithElementRef<HTMLButtonAttributes>;
export type PrimitiveInputAttributes = WithElementRef<HTMLInputAttributes>;
export type PrimitiveSpanAttributes = WithElementRef<
	HTMLAttributes<HTMLSpanElement>
>;
export type PrimitiveTextareaAttributes =
	WithElementRef<HTMLTextareaAttributes>;
export type PrimitiveHeadingAttributes = WithElementRef<
	HTMLAttributes<HTMLHeadingElement>
>;
// This is a generic type that can be used to represent any HTML header element <header>
export type PrimitiveHeaderAttributes = WithElementRef<
	HTMLAttributes<HTMLElement>
>;

// This is a generic type that can be used to represent any HTML footer element <footer>
export type PrimitiveFooterAttributes = WithElementRef<
	HTMLAttributes<HTMLElement>
>;

export type PrimitiveParagraphAttributes = WithElementRef<
	HTMLAttributes<HTMLParagraphElement>
>;
export type PrimitiveCanvasAttributes = WithElementRef<
	HTMLAttributes<HTMLCanvasElement>
>;
export type PrimitiveLiAttributes = WithElementRef<HTMLLiAttributes>;
export type PrimitiveOlAttributes = WithElementRef<HTMLOlAttributes>;
export type PrimitiveLabelAttributes = WithElementRef<HTMLLabelAttributes>;
export type PrimitiveUlAttributes = WithElementRef<
	HTMLAttributes<HTMLUListElement>
>;
export type PrimitiveTableAttributes = WithElementRef<HTMLTableAttributes>;
export type PrimitiveTdAttributes = WithElementRef<HTMLTdAttributes>;
export type PrimitiveTrAttributes = WithElementRef<
	HTMLAttributes<HTMLTableRowElement>
>;
export type PrimitiveThAttributes = WithElementRef<HTMLThAttributes>;
export type PrimitiveFigureAttributes = WithElementRef<
	HTMLAttributes<HTMLElement>
>;
export type PrimitiveTableSectionAttributes = WithElementRef<
	HTMLAttributes<HTMLTableSectionElement>
>;
export type PrimitiveImgAttributes = WithElementRef<HTMLImgAttributes>;
export type PrimitiveSvgAttributes = WithElementRef<
	SVGAttributes<SVGSVGElement>
>;
export type PrimitiveVideoAttributes = WithElementRef<
	HTMLAttributes<HTMLVideoElement>
>;

export type ButtonClickEvent =
	| (MouseEventHandler<HTMLButtonElement> &
			MouseEventHandler<HTMLAnchorElement>)
	| null;
