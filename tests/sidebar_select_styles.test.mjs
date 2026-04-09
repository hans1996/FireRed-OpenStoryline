import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const testDir = path.dirname(fileURLToPath(import.meta.url));
const cssPath = path.resolve(testDir, "../web/static/style.css");
const css = fs.readFileSync(cssPath, "utf8");

test("sidebar model select keeps explicit background and text colors", () => {
  assert.match(css, /\.sidebar-model-select\s*\{[\s\S]*background(?:-color)?:\s*var\(--surface-2\)/);
  assert.match(css, /\.sidebar-model-select\s*\{[\s\S]*color:\s*var\(--text\)/);
  assert.match(css, /\.sidebar-model-select:focus\s*\{[\s\S]*box-shadow:\s*var\(--ring\)/);
});
