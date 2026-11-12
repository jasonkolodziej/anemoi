/** `lon` shifted by a whole number of turns to lie within 180 degrees of
 * `refLon`, so a track crossing the antimeridian stays continuous
 * (..., 179, 181, ...) rather than jumping by 360. MapLibre draws a
 * longitude past +/-180 on the neighbouring world copy. */
export function unwrapLon(lon: number, refLon: number): number {
	return lon + 360 * Math.round((refLon - lon) / 360);
}
