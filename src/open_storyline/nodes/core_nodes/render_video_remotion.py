"""
render_video_remotion.py - Remotion-based video rendering node for OpenStoryline.
Renders high-quality animated video using Remotion (React-based framework).
"""
import json
import os
import subprocess
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from open_storyline.utils.register import NODE_REGISTRY
from open_storyline.nodes.core_nodes.base_node import BaseNode, NodeMeta
from open_storyline.nodes.node_state import NodeState
from open_storyline.utils.logging import get_logger

logger = get_logger(__name__)


@NODE_REGISTRY.register("render_video_remotion")
class RenderVideoRemotionNode(BaseNode):
    """Render high-quality video using Remotion with animations, transitions, and effects."""
    meta = NodeMeta(
        name="render_video_remotion",
        description="Render high-quality video using Remotion with animations, transitions, and effects",
        node_id="render_video_remotion",
        node_kind="render",
        require_prior_kind=["plan_timeline", "load_media"],
        default_require_prior_kind=["plan_timeline", "load_media"],
        next_available_node=["finish"],
    )

    def __init__(self, server_cfg):
        super().__init__(server_cfg)
        project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
        self.remotion_dir = project_root / "remotion-project"
        self.remotion_script = self.remotion_dir / "scripts" / "render_timeline.js"

    def _ensure_node_installed(self) -> bool:
        node_modules = self.remotion_dir / "node_modules" / "remotion"
        if not node_modules.exists():
            logger.warning("Remotion deps not found, running npm install...")
            try:
                subprocess.run(["npm", "install"], cwd=str(self.remotion_dir),
                              check=True, capture_output=True, timeout=120)
                return True
            except Exception as e:
                logger.error(f"npm install failed: {e}")
                return False
        return True

    def _build_timeline_data(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        timeline = inputs.get("plan_timeline", {})
        load_media = inputs.get("load_media", {})
        media_map = {}
        for item in (load_media.get("videos") or []) + (load_media.get("images") or []):
            mid = item.get("media_id")
            mpath = item.get("path", "")
            if mid and mpath and not mpath.startswith("http"):
                media_map[mid] = mpath

        total_duration = 0
        video_items = []
        for item in timeline.get("tracks", {}).get("video", []):
            start = item.get("start", 0)
            duration = item.get("duration", 3000)
            end = start + duration
            media_id = item.get("media_id", item.get("clip_id", ""))
            media_path = media_map.get(media_id, "")
            if not media_path:
                continue
            video_items.append({
                "media_id": media_id,
                "media_type": item.get("media_type", "image"),
                "path": media_path,
                "start": start, "end": end, "duration": duration,
                "caption": item.get("caption", ""),
                "transition": item.get("transition", "fade"),
                "transition_duration": item.get("transition_duration", 500),
            })
            total_duration = max(total_duration, end)

        if total_duration == 0:
            total_duration = 5000

        ar = inputs.get("aspect_ratio", "16:9")
        if isinstance(ar, str) and ":" in ar:
            p = ar.split(":")
            ar = float(p[0]) / float(p[1])
        else:
            try: ar = float(ar)
            except: ar = 16 / 9

        max_dim = 1080
        try: max_dim = int(inputs.get("output_max_dimension_px", 1080))
        except: max_dim = 1080

        if ar >= 1.0: width = max_dim; height = max(2, round(width / ar))
        else: height = max_dim; width = max(2, round(height * ar))

        def even(v): v = max(2, int(v)); return v - (v % 2)
        width, height = even(width), even(height)

        subtitles = []
        for unit in timeline.get("subtitles", []):
            subtitles.append({"unit_id": unit.get("unit_id", ""), "index_in_group": unit.get("index_in_group", 0),
                              "text": unit.get("text", ""), "start_ms": unit.get("start", 0), "end_ms": unit.get("end", 0)})

        return {
            "fps": 25, "width": width, "height": height, "total_duration": total_duration,
            "tracks": {"video": video_items, "bgm": [], "voiceover": []},
            "subtitles": subtitles,
            "style": {"bg_color": inputs.get("bg_color", [0,0,0]), "font_color": inputs.get("font_color", [255,255,255]),
                      "font_size": 40, "transition_duration": 500, "layout_mode": "fit"},
        }

    def _render_with_remotion(self, timeline_data, output_dir):
        if not self._ensure_node_installed():
            return None
        output_file = output_dir / f"remotion_{uuid.uuid4().hex[:8]}.mp4"
        props_file = output_dir / f"timeline_{uuid.uuid4().hex[:8]}.json"
        props_file.write_text(json.dumps({"timelineData": timeline_data}, indent=2, ensure_ascii=False))
        logger.info(f"Timeline written to {props_file}")

        cmd = ["node", str(self.remotion_script), "--timeline", str(props_file),
               "--output", str(output_file), "--fps", str(timeline_data["fps"]),
               "--width", str(timeline_data["width"]), "--height", str(timeline_data["height"])]
        logger.info(f"Running: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, cwd=str(self.remotion_dir),
                                   capture_output=True, text=True, timeout=300)
            if result.stdout: logger.info(f"Remotion: {result.stdout[-500:]}")
            if result.returncode == 0 and output_file.exists():
                try: return str(output_file.relative_to(Path.cwd()))
                except: return str(output_file)
            return None
        except Exception as e:
            logger.error(f"Remotion error: {e}")
            return None

    async def process(self, node_state, inputs):
        output_dir = self._prepare_output_directory(node_state)
        data = self._build_timeline_data(inputs)
        if not data["tracks"]["video"]:
            return {"success": False, "error": "No clips", "output_video_path": None}
        path = self._render_with_remotion(data, output_dir)
        if path:
            return {"success": True, "output_video_path": path, "render_method": "remotion",
                    "width": data["width"], "height": data["height"],
                    "duration_ms": data["total_duration"], "n_clips": len(data["tracks"]["video"])}
        return {"success": False, "error": "Render failed", "output_video_path": None}

    async def default_process(self, node_state, inputs):
        return {"success": True, "output_video_path": None, "render_method": "skipped"}
