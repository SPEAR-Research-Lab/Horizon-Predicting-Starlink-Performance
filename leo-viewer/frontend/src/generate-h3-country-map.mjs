import fs from "fs";
import * as h3 from "h3-js";
import area from "@turf/area";
import intersect from "@turf/intersect";
import { polygon } from "@turf/helpers";
import { flatten } from "@turf/turf";
import rewind from "@turf/rewind";

const countries = JSON.parse(
  fs.readFileSync("./src/countries.geojson", "utf8"),
);
const resolutions = [2, 3, 4, 5];
const result = {};

for (const res of resolutions) {
  console.log(`Processing resolution ${res}...`);
  result[res] = {};

  for (const feature of countries.features) {
    const name =
      feature.properties.ADMIN || feature.properties.name || "Unknown";
    if (
      !feature.geometry ||
      !["Polygon", "MultiPolygon"].includes(feature.geometry.type)
    )
      continue;

    const rewound = rewind(feature, { reverse: false });
    const flattened = flatten(rewound).features;

    for (const poly of flattened) {
      let hexes;
      try {
        hexes = h3.polygonToCells(poly.geometry, res, true);
      } catch (err) {
        console.warn(
          `Failed to polyfill for ${name} at resolution ${res}`,
          err.message,
        );
        continue;
      }

      if (!hexes.length) {
        console.warn(`No hexes for ${name} @ res ${res}`);
        continue;
      }

      for (const h3Index of hexes) {
        const hexBoundary = h3.cellToBoundary(h3Index, true);
        const ring = [...hexBoundary, hexBoundary[0]];
        const hexPolygon = polygon([ring]);

        let overlap;
        try {
          overlap = intersect(hexPolygon, poly);
        } catch {
          continue;
        }

        if (overlap) {
          const overlapArea = area(overlap);
          const hexArea = area(hexPolygon);
          const pct = +(100 * (overlapArea / hexArea)).toFixed(1);

          if (pct > 0.1) {
            if (!result[res][h3Index]) result[res][h3Index] = {};
            result[res][h3Index][name] = pct;
          }
        }
      }
    }
  }

  const count = Object.keys(result[res]).length;
  console.log(`Done with resolution ${res} (${count} hexes)`);
}

fs.writeFileSync("./public/h3-country-coverage.json", JSON.stringify(result));
console.log("🎉 Wrote h3-country-coverage.json");
