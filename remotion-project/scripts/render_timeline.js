#!/usr/bin/env node
/**
 * CLI: render_timeline.js
 * Called by OpenStoryline's Python remotion node.
 * Usage: node scripts/render_timeline.js --timeline <path> --output <path> --fps 25 --width 1280 --height 720
 */
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const args = process.argv.slice(2);
const params = {};
for (let i = 0; i < args.length; i++) {
  if (args[i].startsWith('--') && i + 1 < args.length) {
    params[args[i].slice(2)] = args[i + 1];
    i++;
  }
}

if (!params.timeline) { console.error('Error: --timeline <path> required'); process.exit(1); }
if (!fs.existsSync(params.timeline)) { console.error('Timeline not found: ' + params.timeline); process.exit(1); }

const output = params.output || path.join(path.dirname(params.timeline), 'output.mp4');
const fps = params.fps || 25;
const w = params.width || 1920;
const h = params.height || 1080;

const data = JSON.parse(fs.readFileSync(params.timeline, 'utf-8'));

// Ensure output dir exists
const outDir = path.dirname(output);
if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

// Call Remotion CLI directly
const cmd = `npx remotion render src/index.ts TimelineComposition "${output}" --props='${JSON.stringify(data)}' --fps=${fps} --width=${w} --height=${h} --overwrite`;
console.log('Running Remotion render...');
execSync(cmd, { cwd: path.join(__dirname, '..'), stdio: 'inherit', timeout: 10 * 60 * 1000 });
console.log('Render complete:', output);
