/**
 * URL to the GeoJSON file containing world countries data.
 */

export const WORLD_GEOJSON =
  "https://cdn.jsdelivr.net/gh/nvkelso/natural-earth-vector@v5.1.2/geojson/ne_110m_admin_0_countries.geojson";

export interface WorldFeatureProperties {
  NAME_LONG: string;
}

export type WorldData = GeoJSON.FeatureCollection<
  GeoJSON.Geometry,
  WorldFeatureProperties
>;

/**
 * Fetches world countries data as a GeoJSON FeatureCollection.
 * @param src uri to source the world data
 * @returns Promise resolving to the world data as a GeoJSON FeatureCollection of WorldFeatureProperties.
 */
export const useWorldData = async (src: string = WORLD_GEOJSON): Promise<WorldData> => {
  const response = await fetch(src);
  if (!response.ok) {
    throw new Error(`Failed to fetch world data: ${response.statusText}`);
  }
  const data: WorldData = await response.json();
  return data;
};
