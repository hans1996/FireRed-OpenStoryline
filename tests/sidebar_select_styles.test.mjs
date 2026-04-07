import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const css = fs.readFileSync(
  "/media/hans/DATA/FireRed-OpenStoryline/web/static/style.css",
  "utf8",
);

test("sidebar model select defines dark-friendly popup option colors", () => {
  assert.match(css, /\.sidebar-model-select\s*\{[\s\S]*color-scheme:/);
  assert.match(css, /\.sidebar-model-select\s+option\s*,\s*[\r\n\s]*\.sidebar-model-select\s+optgroup\s*\{[\s\S]*background(?:-color)?:/);
  assert.match(css, /\.sidebar-model-select\s+option\s*,\s*[\r\n\s]*\.sidebar-model-select\s+optgroup\s*\{[\s\S]*color:/);
});
