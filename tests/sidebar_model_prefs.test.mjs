import test from "node:test";
import assert from "node:assert/strict";

import { chooseSidebarModelSelection } from "../web/static/sidebar_model_prefs.js";

test("prefers persisted model for blank sessions when available", () => {
  const picked = chooseSidebarModelSelection({
    availableModels: ["gemma4:31b-it-q4_K_M", "gemini-3.1-flash-lite-preview"],
    snapshotModel: "gemma4:31b-it-q4_K_M",
    persistedModel: "gemini-3.1-flash-lite-preview",
    preferPersisted: true,
  });

  assert.equal(picked, "gemini-3.1-flash-lite-preview");
});

test("keeps snapshot model for non-blank sessions", () => {
  const picked = chooseSidebarModelSelection({
    availableModels: ["gemma4:31b-it-q4_K_M", "gemini-3.1-flash-lite-preview"],
    snapshotModel: "gemma4:31b-it-q4_K_M",
    persistedModel: "gemini-3.1-flash-lite-preview",
    preferPersisted: false,
  });

  assert.equal(picked, "gemma4:31b-it-q4_K_M");
});

test("falls back cleanly when persisted model is unavailable", () => {
  const picked = chooseSidebarModelSelection({
    availableModels: ["gemma4:31b-it-q4_K_M"],
    snapshotModel: "gemma4:31b-it-q4_K_M",
    persistedModel: "gemini-3.1-flash-lite-preview",
    preferPersisted: true,
  });

  assert.equal(picked, "gemma4:31b-it-q4_K_M");
});
