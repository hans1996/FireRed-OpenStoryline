# Remotion Video Rendering Integration

## Overview
This project uses Remotion (React-based framework) to generate high-quality
animated videos as a replacement or complement to MoviePy rendering.

## Architecture
```
plan_timeline (JSON) → render_video_remotion.py (Python node)
  → writes timeline_props.json
  → calls node render_timeline.js
  → npx remotion render
  → MP4 output
```

## File Structure
```
remotion-project/
├── package.json              # Remotion v4.0.427 deps
├── tsconfig.json
├── src/
│   ├── index.ts              # Entry point
│   ├── Root.tsx              # Composition registration
│   ├── TimelineComposition.tsx  # Core animation component
│   └── timeline_schema.ts    # Zod schema: Python↔Remotion data contract
├── public/assets/            # Media assets (served by Remotion server)
├── scripts/render_timeline.js # CLI render script
└── .gitignore
```

## Usage
```python
from open_storyline.nodes.core_nodes.render_video_remotion import RenderVideoRemotionNode
node = RenderVideoRemotionNode(settings)
result = await node.process(node_state, inputs)
```

## Supported Transitions
fade, slide-left, slide-right, slide-up, slide-down, zoom-in, zoom-out, none

## Notes
- Media files must be placed in remotion-project/public/
- Paths are relative (e.g. assets/filename.png)
- Requires Node.js >= 16
