from __future__ import annotations

import base64
import json
import os
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
import urllib.parse
import urllib.request

from design_intelligence import DESIGN_PLAYBOOK, FEW_SHOT_PATTERNS

from flask import Flask, jsonify, request

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

ROOT = Path(__file__).resolve().parent


def load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


load_env_file(ROOT / ".env")

app = Flask(__name__)
TOKEN = os.getenv("CLYP_AI_INTERNAL_TOKEN", "change-me")
API_KEY = os.getenv("CLYP_GEMINI_API_KEY", "").strip()
MODEL = os.getenv("CLYP_GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
IMAGE_MODEL = os.getenv("CLYP_GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image").strip() or "gemini-3.1-flash-image"
IMAGE_FALLBACK_MODEL = os.getenv("CLYP_GEMINI_IMAGE_FALLBACK_MODEL", "gemini-3.1-flash-lite-image").strip() or "gemini-3.1-flash-lite-image"
AI_ENDPOINT = os.getenv("CLYP_AI_ENDPOINT", "http://127.0.0.1:8100").strip() or "http://127.0.0.1:8100"
OPENVERSE = "https://api.openverse.org/v1/images/"
STOCK_FALLBACK_ENABLED = os.getenv("CLYP_STOCK_FALLBACK", "1").strip().lower() not in {"0", "false", "no", "off"}
AUTO_POLISH_SPARSE = os.getenv("CLYP_AUTO_POLISH_SPARSE", "1").strip().lower() not in {"0", "false", "no", "off"}
MIN_FIRST_PASS_LAYERS = max(8, int(os.getenv("CLYP_MIN_DESIGN_LAYERS", "12") or 12))

_IMAGE_MODEL_ALIASES = {
    "gemini-2.5-flash-preview-image": "gemini-2.5-flash-image",
    "gemini-2.5-flash-image-preview": "gemini-2.5-flash-image",
    "gemini-3.1-flash-image-preview": "gemini-3.1-flash-image",
}
IMAGE_MODEL = _IMAGE_MODEL_ALIASES.get(IMAGE_MODEL, IMAGE_MODEL)
IMAGE_FALLBACK_MODEL = _IMAGE_MODEL_ALIASES.get(IMAGE_FALLBACK_MODEL, IMAGE_FALLBACK_MODEL)


def authorised(req) -> bool:
    return req.headers.get("X-Internal-Token") == TOKEN


def get_client():
    if genai is None:
        raise RuntimeError("google-genai is not installed. Run: py -m pip install -r requirements.txt")
    if not API_KEY:
        raise RuntimeError("CLYP_GEMINI_API_KEY is missing from .env")
    return genai.Client(api_key=API_KEY)


DESIGN_OUTPUT_RULES = r"""
Return ONLY one JSON object. Do not use Markdown or code fences.
Use this Clyp editable design contract. Omit optional properties when not needed:
{
  "name": "short project name",
  "design": {
    "canvas": {"width": 432, "height": 540, "bg": "#RRGGBB"},
    "palette": {
      "strategy": "monochromatic|analogous|complementary|split-complementary|triadic",
      "dominant": "#RRGGBB", "support": "#RRGGBB", "accent": "#RRGGBB",
      "light": "#RRGGBB", "dark": "#RRGGBB"
    },
    "layers": [
      {
        "type": "text|shape|image|icon",
        "name": "layer name",
        "x": 0, "y": 0, "w": 100, "h": 50, "opacity": 1, "rotation": 0,

        "text": "text content for text",
        "size": 28, "weight": 600, "color": "#RRGGBB",
        "spacing": 0, "line": 1.05, "font": "font name", "align": "left|center|right",
        "text_stroke_color": "#RRGGBB", "text_stroke_width": 0,
        "shadow_color": "#RRGGBB", "shadow_opacity": 0, "shadow_x": 0, "shadow_y": 8, "shadow_blur": 18,

        "kind": "rect|rounded|ellipse|pill|line|dashed-line|triangle|diamond|pentagon|hexagon|octagon|star|burst|arrow|chevron|ribbon|semicircle|parallelogram|trapezoid|pattern-dots|pattern-lines|pattern-grid|pattern-checker|pattern-cross",
        "fill": "solid|linear|radial", "color2": "#RRGGBB", "gradient_angle": 135,
        "radius": "0 or CSS radius", "stroke_color": "#RRGGBB", "stroke_width": 0,

        "icon": "calendar|clock|map-pin|phone|mail|globe|link|user|users|mic|music|camera|shopping-bag|tag|home|building|briefcase|graduation-cap|book|trophy|football|utensils|leaf|bolt|shield|lock|ticket|megaphone|gift|play|instagram|facebook|youtube|linkedin|whatsapp|x-social|check|arrow-right|star|heart|cross|spark",

        "asset_prompt": "ONLY for image layers that Clyp should generate; describe the photo/illustration asset without flyer text",
        "stock_query": "2-6 concrete stock-search keywords describing the same subject",
        "fit": "cover|contain", "blend_mode": "normal|multiply|screen|overlay|soft-light",
        "mask": "none|fade-bottom|fade-left|fade-right|soft-ellipse",
        "brightness": 1, "contrast": 1, "saturation": 1, "blur": 0
      }
    ]
  },
  "critique": {
    "direction": "one-sentence art direction",
    "hierarchy": "brief note", "colour": "brief note", "imagery": "brief note",
    "spacing": "brief note", "contrast": "brief note", "readability": "brief note"
  }
}
A normal professional flyer should usually contain 12-28 purposeful editable layers, including 5-12 non-text visual layers (image, shape, icon, overlay, rule, glow, frame, badge, pattern, or information structure). A consciously minimalist brief may use fewer, but never return a visually unfinished canvas with only a headline and two details.
Use visual layers to create depth and structure, not filler: hero image or image frame when appropriate; readability overlay; restrained atmospheric light; accent rule/bar; frame/rail; one consistent motif; information icons; CTA/detail grouping; controlled pattern or corner geometry when the category supports it.
If imagery is genuinely useful, include at most ONE generated hero image layer in the first direction. Give it a precise asset_prompt AND concise stock_query so Clyp can fall back to licensed stock imagery when image-generation quota is unavailable. Compose text/shapes around it. Do not ask the image model to render flyer typography, event details, logo or CTA.
Use image treatment fields intentionally; a photo should look integrated rather than pasted on.
Use icon layers for practical information such as time, date, location, phone, web/social or one meaningful decorative symbol. Do not scatter icons randomly.
For line shapes, h is thickness. For polygon shapes, x/y/w/h define the editable box.
"""


RECONSTRUCTION_OUTPUT_RULES = r"""
Return ONLY one JSON object. Do not use Markdown or code fences.
This is a tracing/reconstruction task, NOT a redesign task.
Use this compact Clyp reconstruction contract:
{
  "name": "short project name",
  "design": {
    "canvas": {"width": 405, "height": 540, "bg": "#RRGGBB"},
    "layers": [
      {
        "type": "text, shape, or image",
        "name": "descriptive layer name",
        "x": 0, "y": 0, "w": 100, "h": 50,
        "text": "exact visible text when type is text",
        "size": 28, "weight": 600,
        "color": "#RRGGBB",
        "spacing": 0, "line": 1.0,
        "font": "Impact, Arial Narrow, Arial Black, Arial, Georgia, Times New Roman, Trebuchet MS, Verdana, or system-ui",
        "align": "left, center, or right",
        "rotation": 0,
        "radius": "optional CSS radius",
        "opacity": 1,
        "kind": "rect|ellipse|pill|line|triangle for shape layers",
        "fill": "solid|linear for shape layers",
        "color2": "#RRGGBB", "gradient_angle": 135,
        "stroke_color": "#RRGGBB", "stroke_width": 0,
        "text_stroke_color": "#RRGGBB", "text_stroke_width": 0,
        "shadow_color": "#RRGGBB", "shadow_opacity": 0, "shadow_x": 0, "shadow_y": 8, "shadow_blur": 18,
        "brightness": 1, "contrast": 1, "saturation": 1, "blur": 0,
        "crop": [0, 0, 1000, 1000]
      }
    ]
  },
  "critique": {"fidelity": "brief note about what was traced vs approximated"}
}
For image layers, crop is [left, top, right, bottom] in NORMALISED SOURCE coordinates from 0 to 1000.
Image layers always refer to the uploaded source image; do not invent an external URL.
Use image layers for photographs, logos, icons, textured lighting, brush strokes, glows and other complex graphics that cannot be faithfully represented by simple editable primitives.
Use text layers for editable headline/body copy and transcribe it exactly.
Use shape layers only for genuinely simple solid rectangles, lines, circles, pills or blocks.
Return layers in visual back-to-front z-order.
Use as many layers as needed for fidelity, typically 10-30. Fidelity matters more than minimal layer count.
Do not include the same source text both inside a large image crop and again as an editable text layer unless unavoidable. Prefer image crops for photos/logos/icons; prefer editable layers for headline/body copy.
"""


def parse_json_response(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        left, right = raw.find("{"), raw.rfind("}")
        if left < 0 or right <= left:
            raise RuntimeError("Gemini returned an empty or non-JSON design response.")
        parsed = json.loads(raw[left:right + 1])
    if not isinstance(parsed, dict):
        raise RuntimeError("Gemini returned JSON, but not a Clyp design object.")
    return parsed


def safe_hex(value: Any, fallback: str) -> str:
    value = str(value or "").strip()
    return value if re.fullmatch(r"#[0-9A-Fa-f]{6}", value) else fallback


def clamp_int(value: Any, minimum: int, maximum: int, fallback: int) -> int:
    try:
        value = int(round(float(value)))
    except (TypeError, ValueError):
        return fallback
    return max(minimum, min(maximum, value))


def clamp_float(value: Any, minimum: float, maximum: float, fallback: float) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(minimum, min(maximum, value))


def safe_font(value: Any) -> str:
    raw = str(value or "system-ui").strip()[:80]
    allowed_names = [
        # Display / condensed
        "Bebas Neue", "Anton", "Archivo Black", "Barlow Condensed", "League Spartan", "Oswald",
        "Teko", "Big Shoulders Display", "Alfa Slab One", "Bungee", "Abril Fatface", "Fjalla One",
        "Staatliches", "Black Ops One", "Russo One", "Archivo Narrow", "IBM Plex Sans Condensed",
        "Saira Condensed", "Unbounded", "Righteous", "Orbitron", "Chakra Petch", "Syncopate",
        # Modern sans
        "Inter", "Manrope", "Plus Jakarta Sans", "DM Sans", "Poppins", "Montserrat", "Work Sans",
        "Source Sans 3", "Space Grotesk", "Sora", "Outfit", "Urbanist", "Raleway", "Figtree",
        "Nunito Sans", "Lato", "Roboto Condensed", "Mulish", "Rubik", "Karla", "Public Sans",
        "IBM Plex Sans", "Assistant", "Barlow", "Archivo", "Cabin", "Lexend", "Noto Sans",
        # Editorial / premium serif
        "Playfair Display", "DM Serif Display", "Cormorant Garamond", "Libre Baskerville", "Merriweather",
        "Bodoni Moda", "Cinzel", "Lora", "EB Garamond", "Spectral", "Crimson Pro", "Prata",
        "Italiana", "Marcellus", "Cormorant", "Cardo", "Source Serif 4",
        # System fallbacks
        "Impact", "Arial Black", "Arial Narrow", "Arial", "Georgia", "Times New Roman", "Trebuchet MS",
        "Verdana", "system-ui"
    ]
    allowed = {name.lower(): name for name in allowed_names}
    return allowed.get(raw.lower(), "system-ui")


def safe_choice(value: Any, allowed: set[str], fallback: str) -> str:
    raw = str(value or fallback).strip().lower()
    return raw if raw in allowed else fallback


def safe_radius(value: Any, fallback: str = "0") -> str:
    raw = str(value if value is not None else fallback).strip()[:30]
    if re.fullmatch(r"(?:\d+(?:\.\d+)?(?:px|%)?)(?:\s+\d+(?:\.\d+)?(?:px|%)?){0,3}", raw):
        return raw
    return fallback


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = safe_hex(value, "#000000")[1:]
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def relative_luminance(value: str) -> float:
    rgb = [c / 255.0 for c in hex_to_rgb(value)]
    linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in rgb]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(a: str, b: str) -> float:
    la, lb = relative_luminance(a), relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def design_quality_summary(design: dict[str, Any]) -> dict[str, Any]:
    layers = design.get("layers") or []
    text_layers = [l for l in layers if isinstance(l, dict) and l.get("type") == "text"]
    fonts = sorted({str(l.get("font") or "system-ui") for l in text_layers})
    colours = sorted({str(l.get("color")) for l in layers if isinstance(l, dict) and l.get("color")})
    canvas_bg = str((design.get("canvas") or {}).get("bg") or "#FFFFFF")
    low_contrast = []
    for l in text_layers:
        # This is a conservative canvas-background check. When text is over a panel/image,
        # the model's own quality gate remains responsible for local contrast.
        ratio = contrast_ratio(str(l.get("color") or "#111111"), canvas_bg)
        size = float(l.get("size") or 16)
        weight = int(l.get("weight") or 400)
        threshold = 3.0 if size >= 24 or (size >= 19 and weight >= 700) else 4.5
        if ratio < threshold:
            low_contrast.append({"name": l.get("name"), "ratio": round(ratio, 2), "threshold": threshold})
    score = 100
    if len(fonts) > 2:
        score -= min(18, (len(fonts) - 2) * 6)
    if len(colours) > 8:
        score -= min(12, (len(colours) - 8) * 2)
    score -= min(24, len(low_contrast) * 4)
    tiny = [l for l in text_layers if float(l.get("size") or 16) < 9]
    score -= min(16, len(tiny) * 4)
    visual_layers = [l for l in layers if isinstance(l, dict) and l.get("type") in {"shape", "image", "icon"}]
    return {
        "score": max(0, score),
        "layer_count": len(layers),
        "visual_layer_count": len(visual_layers),
        "text_layer_count": len(text_layers),
        "font_families": fonts,
        "colour_count": len(colours),
        "low_contrast_canvas_checks": low_contrast[:8],
        "tiny_text_layers": [l.get("name") for l in tiny[:8]],
    }


def canvas_for_format(fmt: str) -> tuple[int, int, str]:
    f = (fmt or "").lower()
    if "square" in f or "1080 × 1080" in f or "1080x1080" in f:
        return 432, 432, "1080 × 1080"
    if "story" in f or "1920" in f:
        return 432, 768, "1080 × 1920"
    if "a4" in f:
        return 432, 611, "A4"
    return 432, 540, "1080 × 1350"


def reconstruction_canvas(source_w: int, source_h: int) -> tuple[int, int]:
    if source_w <= 0 or source_h <= 0:
        return 432, 540
    max_w, max_h = 720, 540
    scale = min(max_w / source_w, max_h / source_h)
    return max(240, round(source_w * scale)), max(240, round(source_h * scale))


def normalise_crop(value: Any) -> list[int] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    vals = [clamp_int(v, 0, 1000, 0) for v in value]
    left, top, right, bottom = vals
    if right <= left + 2 or bottom <= top + 2:
        return None
    return [left, top, right, bottom]


def normalise_design(
    payload: dict[str, Any],
    fmt: str | None = None,
    canvas_override: tuple[int, int] | None = None,
    allow_images: bool = False,
) -> dict[str, Any]:
    result = payload if isinstance(payload, dict) else {}
    raw_design = result.get("design") if isinstance(result.get("design"), dict) else result
    raw_canvas = raw_design.get("canvas") if isinstance(raw_design.get("canvas"), dict) else {}
    default_w, default_h, canonical_format = canvas_for_format(fmt or "")
    if canvas_override:
        default_w, default_h = canvas_override
        canonical_format = f"Source · {default_w} × {default_h}"
    width = clamp_int(raw_canvas.get("width"), 240, 900, default_w)
    height = clamp_int(raw_canvas.get("height"), 240, 1200, default_h)
    if canvas_override:
        width, height = default_w, default_h

    layers: list[dict[str, Any]] = []
    allowed_types = {"text", "shape", "icon", "image"} if allow_images else {"text", "shape", "icon"}
    for idx, raw in enumerate(raw_design.get("layers") or []):
        if not isinstance(raw, dict):
            continue
        layer_type = str(raw.get("type") or "shape").lower()
        if layer_type not in allowed_types:
            layer_type = "shape"
        layer: dict[str, Any] = {
            "type": layer_type,
            "name": str(raw.get("name") or f"Layer {idx + 1}")[:100],
            "x": clamp_int(raw.get("x"), -200, width + 100, 20),
            "y": clamp_int(raw.get("y"), -200, height + 100, 20),
            "w": clamp_int(raw.get("w"), 4, width + 300, 120),
            "h": clamp_int(raw.get("h"), 4, height + 300, 60),
            "opacity": clamp_float(raw.get("opacity"), 0.02, 1.0, 1.0),
            "rotation": clamp_float(raw.get("rotation"), -180.0, 180.0, 0.0),
        }
        if layer_type == "text":
            layer.update({
                "text": str(raw.get("text") or "Text")[:1200],
                "size": clamp_int(raw.get("size"), 6, 220, 28),
                "weight": clamp_int(raw.get("weight"), 200, 900, 600),
                "color": safe_hex(raw.get("color"), "#111111"),
                "spacing": clamp_float(raw.get("spacing"), -5.0, 20.0, 0.0),
                "line": clamp_float(raw.get("line"), 0.65, 2.4, 1.05),
                "font": safe_font(raw.get("font")),
                "align": str(raw.get("align") or "left").lower() if str(raw.get("align") or "left").lower() in {"left", "center", "right"} else "left",
                "text_stroke_color": safe_hex(raw.get("text_stroke_color"), "#000000"),
                "text_stroke_width": clamp_float(raw.get("text_stroke_width"), 0.0, 8.0, 0.0),
                "shadow_color": safe_hex(raw.get("shadow_color"), "#000000"),
                "shadow_opacity": clamp_float(raw.get("shadow_opacity"), 0.0, 0.9, 0.0),
                "shadow_x": clamp_float(raw.get("shadow_x"), -40.0, 40.0, 0.0),
                "shadow_y": clamp_float(raw.get("shadow_y"), -40.0, 40.0, 6.0),
                "shadow_blur": clamp_float(raw.get("shadow_blur"), 0.0, 80.0, 18.0),
            })
        elif layer_type == "shape":
            layer.update({
                "kind": safe_choice(raw.get("kind"), {"rect", "rounded", "ellipse", "pill", "line", "dashed-line", "triangle", "diamond", "pentagon", "hexagon", "octagon", "star", "burst", "arrow", "chevron", "ribbon", "semicircle", "parallelogram", "trapezoid", "pattern-dots", "pattern-lines", "pattern-grid", "pattern-checker", "pattern-cross"}, "rect"),
                "fill": safe_choice(raw.get("fill"), {"solid", "linear", "radial"}, "solid"),
                "color": safe_hex(raw.get("color"), "#4E5DFF"),
                "color2": safe_hex(raw.get("color2"), safe_hex(raw.get("color"), "#4E5DFF")),
                "gradient_angle": clamp_float(raw.get("gradient_angle"), 0.0, 360.0, 135.0),
                "radius": safe_radius(raw.get("radius"), "0"),
                "stroke_color": safe_hex(raw.get("stroke_color"), "#000000"),
                "stroke_width": clamp_float(raw.get("stroke_width"), 0.0, 20.0, 0.0),
                "shadow_color": safe_hex(raw.get("shadow_color"), "#000000"),
                "shadow_opacity": clamp_float(raw.get("shadow_opacity"), 0.0, 0.8, 0.0),
                "shadow_x": clamp_float(raw.get("shadow_x"), -60.0, 60.0, 0.0),
                "shadow_y": clamp_float(raw.get("shadow_y"), -60.0, 60.0, 10.0),
                "shadow_blur": clamp_float(raw.get("shadow_blur"), 0.0, 100.0, 24.0),
            })
        elif layer_type == "icon":
            layer.update({
                "icon": safe_choice(raw.get("icon"), {"calendar", "clock", "map-pin", "phone", "mail", "globe", "link", "user", "users", "mic", "music", "camera", "shopping-bag", "tag", "home", "building", "briefcase", "graduation-cap", "book", "trophy", "football", "utensils", "leaf", "bolt", "shield", "lock", "ticket", "megaphone", "gift", "play", "instagram", "facebook", "youtube", "linkedin", "whatsapp", "x-social", "check", "arrow-right", "star", "heart", "cross", "spark"}, "star"),
                "color": safe_hex(raw.get("color"), "#111111"),
                "shadow_color": safe_hex(raw.get("shadow_color"), "#000000"),
                "shadow_opacity": clamp_float(raw.get("shadow_opacity"), 0.0, 0.8, 0.0),
                "shadow_x": clamp_float(raw.get("shadow_x"), -40.0, 40.0, 0.0),
                "shadow_y": clamp_float(raw.get("shadow_y"), -40.0, 40.0, 4.0),
                "shadow_blur": clamp_float(raw.get("shadow_blur"), 0.0, 80.0, 12.0),
            })
        else:
            crop = normalise_crop(raw.get("crop"))
            if crop:
                layer["crop"] = crop
            source_kind = safe_choice(raw.get("source_kind"), {"source", "ai", "local", "online"}, "source" if crop else "ai")
            layer["source_kind"] = source_kind
            if source_kind == "source":
                layer["asset"] = "source_upload"
            elif raw.get("asset"):
                layer["asset"] = str(raw.get("asset"))[:120]
            if raw.get("src"):
                layer["src"] = str(raw.get("src"))[:200000]
            if raw.get("asset_prompt"):
                layer["asset_prompt"] = str(raw.get("asset_prompt"))[:1500]
            if raw.get("stock_query"):
                layer["stock_query"] = str(raw.get("stock_query"))[:180]
            if isinstance(raw.get("attribution"), dict):
                layer["attribution"] = raw.get("attribution")
            layer["radius"] = safe_radius(raw.get("radius"), "0")
            layer["fit"] = safe_choice(raw.get("fit"), {"cover", "contain"}, "cover")
            layer["blend_mode"] = safe_choice(raw.get("blend_mode"), {"normal", "multiply", "screen", "overlay", "soft-light"}, "normal")
            layer["mask"] = safe_choice(raw.get("mask"), {"none", "fade-bottom", "fade-left", "fade-right", "soft-ellipse"}, "none")
            layer["brightness"] = clamp_float(raw.get("brightness"), 0.2, 2.0, 1.0)
            layer["contrast"] = clamp_float(raw.get("contrast"), 0.2, 2.0, 1.0)
            layer["saturation"] = clamp_float(raw.get("saturation"), 0.0, 2.0, 1.0)
            layer["blur"] = clamp_float(raw.get("blur"), 0.0, 20.0, 0.0)
        layers.append(layer)

    if not layers:
        layers = [
            {"type":"shape","name":"Atmospheric glow","kind":"ellipse","fill":"radial","x":width-210,"y":-70,"w":270,"h":270,"color":"#F4C95D","color2":"#1F2445","opacity":0.30,"rotation":0},
            {"type":"shape","name":"Accent rail","kind":"rect","fill":"solid","x":width-54,"y":0,"w":54,"h":height,"color":"#4E5DFF","opacity":0.90,"rotation":0},
            {"type":"shape","name":"Frame","kind":"rect","fill":"solid","x":22,"y":22,"w":width-44,"h":height-44,"color":"#FFFFFF","opacity":0.02,"stroke_color":"#FFFFFF","stroke_width":1,"rotation":0},
            {"type":"shape","name":"Kicker bar","kind":"rect","fill":"solid","x":36,"y":56,"w":36,"h":4,"color":"#F4C95D","opacity":1,"rotation":0},
            {"type":"text","name":"Kicker","x":36,"y":70,"w":280,"h":25,"text":"YOUR IDEA","size":11,"weight":700,"color":"#FFFFFF","spacing":1.5,"line":1.0,"font":"Inter","align":"left","opacity":1,"rotation":0},
            {"type":"text","name":"Headline","x":36,"y":145,"w":330,"h":125,"text":"DESIGNED\nWITH INTENT", "size":50,"weight":800,"color":"#FFFFFF","spacing":-0.4,"line":0.9,"font":"League Spartan","align":"left","opacity":1,"rotation":0},
            {"type":"shape","name":"Headline rule","kind":"line","fill":"solid","x":36,"y":300,"w":80,"h":4,"color":"#F4C95D","opacity":1,"rotation":0},
            {"type":"text","name":"Details","x":36,"y":330,"w":300,"h":55,"text":"Add your event, offer or announcement details here.","size":15,"weight":500,"color":"#FFFFFF","spacing":0,"line":1.25,"font":"Inter","align":"left","opacity":1,"rotation":0},
            {"type":"icon","name":"Detail icon","icon":"arrow-right","x":36,"y":430,"w":22,"h":22,"color":"#F4C95D","opacity":1,"rotation":0},
            {"type":"text","name":"CTA","x":70,"y":432,"w":240,"h":24,"text":"MAKE IT CLEAR. MAKE IT COUNT.","size":10,"weight":700,"color":"#FFFFFF","spacing":0.6,"line":1.0,"font":"Inter","align":"left","opacity":1,"rotation":0},
        ]

    raw_palette = raw_design.get("palette") if isinstance(raw_design.get("palette"), dict) else {}
    palette = {
        "strategy": safe_choice(raw_palette.get("strategy"), {"monochromatic", "analogous", "complementary", "split-complementary", "triadic"}, "complementary"),
        "dominant": safe_hex(raw_palette.get("dominant"), safe_hex(raw_canvas.get("bg"), "#1F2445")),
        "support": safe_hex(raw_palette.get("support"), "#F2F2EE"),
        "accent": safe_hex(raw_palette.get("accent"), "#F4C95D"),
        "light": safe_hex(raw_palette.get("light"), "#FFFFFF"),
        "dark": safe_hex(raw_palette.get("dark"), "#111111"),
    }
    design = {
        "name": str(result.get("name") or raw_design.get("name") or "Untitled design")[:190],
        "format": canonical_format,
        "canvas": {"width": width, "height": height, "bg": safe_hex(raw_canvas.get("bg"), "#1F2445")},
        "palette": palette,
        "layers": layers[:40],
    }
    design["quality"] = design_quality_summary(design)
    return design



def _brief_is_explicitly_minimal(brief: str) -> bool:
    text = (brief or "").lower()
    return any(token in text for token in ("minimalist", "very minimal", "ultra minimal", "extremely minimal", "typography only"))


def design_density_summary(design: dict[str, Any]) -> dict[str, Any]:
    layers = [l for l in (design.get("layers") or []) if isinstance(l, dict)]
    text = [l for l in layers if l.get("type") == "text"]
    visuals = [l for l in layers if l.get("type") in {"shape", "image", "icon"}]
    images = [l for l in layers if l.get("type") == "image"]
    icons = [l for l in layers if l.get("type") == "icon"]
    return {"layers": len(layers), "text": len(text), "visuals": len(visuals), "images": len(images), "icons": len(icons)}


def design_is_sparse(design: dict[str, Any], brief: str) -> bool:
    d = design_density_summary(design)
    if _brief_is_explicitly_minimal(brief):
        return d["layers"] < 6 or d["text"] < 2 or d["visuals"] < 2
    return d["layers"] < MIN_FIRST_PASS_LAYERS or d["text"] < 2 or d["visuals"] < 6


def infer_design_category(brief: str) -> str:
    text = (brief or "").lower()
    groups = [
        ("worship", ("church", "worship", "service", "conference", "crusade", "gospel", "ministry", "sunday")),
        ("food", ("food", "restaurant", "brunch", "burger", "pizza", "menu", "cafe", "meal")),
        ("beauty", ("beauty", "skin", "skincare", "fashion", "salon", "makeup", "spa")),
        ("sale", ("sale", "discount", "promo", "offer", "% off", "clearance", "deal")),
        ("real-estate", ("real estate", "property", "apartment", "house", "open house", "land", "realtor")),
        ("technology", ("technology", "tech", "software", "saas", "developer", "app", "product launch")),
        ("music", ("music", "concert", "nightlife", "dj", "party", "festival", "album")),
        ("corporate", ("corporate", "business", "seminar", "workshop", "company", "conference", "hiring")),
    ]
    for name, tokens in groups:
        if any(token in text for token in tokens):
            return name
    return "general"


def category_blueprint(category: str) -> str:
    return {
        "worship": "Image-led worship scene; full-bleed congregation/worshippers rather than isolated objects; dark readability fade; warm stage light; condensed headline; compact DATE/TIME/VENUE module; dedicated CTA/contact footer; no text overlaps.",
        "food": "Appetising hero crop; warm controlled grade; clear product/offer hierarchy; compact price/CTA module; supporting shapes only where they frame the food or offer.",
        "beauty": "Editorial portrait/product crop; soft light; refined type pairing; generous but shaped negative space; delicate rule/frame; concise CTA; avoid busy patterns.",
        "real-estate": "Property-led hero; trustworthy typography; location/facts module; clear price/CTA; refined frame/overlay; no decorative clutter.",
        "technology": "Crisp grid; modern typography; precise geometry; restrained luminous depth; one strong accent; information modules aligned to a clear axis.",
        "music": "Live performance/crowd hero; controlled dark field; dramatic light; strong event title; date/time/venue grouped; avoid illegible chaos.",
        "corporate": "Grid-led composition; restrained image or architecture/people crop; premium whitespace; one accent; clear date/speaker/venue module; minimal effects.",
        "sale": "Product/offer leads; clear discount/price; product image integrated; energetic accent; CTA obvious; no random burst clutter.",
        "general": "Choose one clear hook; establish a real visual anchor; group related facts; build a complete but restrained visual system; no independent text overlaps.",
    }.get(category, "Choose one clear hook; build a complete visual system; group related facts; no independent text overlaps.")


def _compact_design_for_review(design: dict[str, Any]) -> dict[str, Any]:
    compact = json.loads(json.dumps(design))
    compact.pop("assets", None)
    compact.pop("source", None)
    for layer in compact.get("layers") or []:
        if isinstance(layer, dict) and layer.get("type") == "image":
            if str(layer.get("src") or "").startswith("data:"):
                layer.pop("src", None)
    return compact


def polish_sparse_design(design: dict[str, Any], brief: str, fmt: str) -> tuple[dict[str, Any], str | None]:
    if not AUTO_POLISH_SPARSE or not design_is_sparse(design, brief):
        return design, None
    current = _compact_design_for_review(design)
    prompt = f"""<context>
User brief: {brief}
Current editable Clyp design JSON: {json.dumps(current, separators=(',', ':'))}
</context>
<task>
The first direction is too visually sparse. Return a stronger FULL revised design, not a list of suggestions.
Preserve every factual word, date, time, price, venue, phone, URL and name already present. Preserve any image layer/asset_prompt.
Build a deliberate professional composition with approximately 12-28 purposeful layers unless the user explicitly requested minimalist typography-only work.
Add meaningful visual structure where appropriate: readability overlay, frame/rail, accent rule, information grouping, one repeated motif, restrained glow/gradient, practical icon(s), badge/pill, corner geometry or subtle pattern. Do not add meaningless filler.
Keep one strong focal point, excellent spacing, no edge collisions, no low-contrast small copy, and normally no more than two font families.
Use Clyp's richer shape/icon vocabulary. Return the complete design JSON.
</task>"""
    try:
        raw = call_json(prompt, SYSTEM_DESIGNER, DESIGN_OUTPUT_RULES, temperature=0.38)
        polished = normalise_design(raw, fmt, allow_images=True)
        if design_density_summary(polished)["layers"] > design_density_summary(design)["layers"]:
            return polished, "Clyp automatically strengthened a sparse first direction before opening the editor."
    except Exception:
        pass
    return design, None


def enrich_sparse_design(design: dict[str, Any], brief: str) -> tuple[dict[str, Any], list[str]]:
    """Deterministic final quality guard. Adds only editable, non-factual visual structure."""
    if not design_is_sparse(design, brief):
        return design, []
    layers = design.setdefault("layers", [])
    canvas = design.get("canvas") or {}
    w, h = int(canvas.get("width") or 432), int(canvas.get("height") or 540)
    pal = design.get("palette") or {}
    dominant = safe_hex(pal.get("dominant"), safe_hex(canvas.get("bg"), "#1F2445"))
    accent = safe_hex(pal.get("accent"), "#F4C95D")
    light = safe_hex(pal.get("light"), "#FFFFFF")
    dark = safe_hex(pal.get("dark"), "#111111")
    category = infer_design_category(brief)
    names = {str(l.get("name") or "").lower() for l in layers if isinstance(l, dict)}
    first_text = next((i for i,l in enumerate(layers) if isinstance(l,dict) and l.get("type")=="text"), len(layers))
    has_image = any(isinstance(l,dict) and l.get("type")=="image" for l in layers)
    visual_count = design_density_summary(design)["visuals"]
    additions: list[tuple[int,dict[str,Any]]] = []

    def add(layer: dict[str, Any], position: int | None = None):
        nonlocal visual_count
        if visual_count >= 9 and len(layers) + len(additions) >= MIN_FIRST_PASS_LAYERS:
            return
        lname = str(layer.get("name") or "").lower()
        if lname in names:
            return
        names.add(lname);visual_count += 1
        additions.append((first_text if position is None else position, layer))

    # Image-led designs need a separate readability/depth layer between image and copy.
    if has_image and not any("overlay" in n or "fade" in n for n in names):
        add({"type":"shape","name":"Readability overlay","kind":"rect","fill":"linear","x":0,"y":0,"w":w,"h":h,"color":dark,"color2":dominant,"gradient_angle":90 if dominant_text_side(design)=="left" else 270,"opacity":0.48,"rotation":0}, first_text)

    if category in {"worship","music","technology","beauty"} and not any("glow" in n or "light" in n for n in names):
        add({"type":"shape","name":"Atmospheric light","kind":"ellipse","fill":"radial","x":w-210,"y":-65,"w":280,"h":280,"color":accent,"color2":dominant,"opacity":0.24,"rotation":0,"shadow_color":accent,"shadow_opacity":0.25,"shadow_blur":80}, first_text)

    if not any("frame" in n for n in names):
        add({"type":"shape","name":"Outer frame","kind":"rect","fill":"solid","x":22,"y":22,"w":max(40,w-44),"h":max(40,h-44),"color":light,"opacity":0.02,"stroke_color":light,"stroke_width":1,"rotation":0}, first_text)

    if not any("accent rail" in n or "side rail" in n for n in names):
        rail_w=max(6,round(w*0.018))
        add({"type":"shape","name":"Accent rail","kind":"rect","fill":"solid","x":0,"y":0,"w":rail_w,"h":h,"color":accent,"opacity":0.92,"rotation":0}, first_text)

    if not any("accent rule" in n or "headline rule" in n or "divider" in n for n in names):
        add({"type":"shape","name":"Accent rule","kind":"line","fill":"solid","x":round(w*.08),"y":round(h*.56),"w":round(w*.18),"h":4,"color":accent,"opacity":1,"rotation":0}, first_text)

    if category in {"worship","music","sale","technology"} and not any("pattern" in n for n in names):
        add({"type":"shape","name":"Texture pattern","kind":"pattern-dots","fill":"solid","x":round(w*.68),"y":round(h*.68),"w":round(w*.25),"h":round(h*.18),"color":accent,"opacity":0.22,"rotation":0}, first_text)

    # Add practical icons only when the corresponding facts already exist.
    joined = " ".join(str(l.get("text") or "") for l in layers if isinstance(l,dict) and l.get("type")=="text").lower()
    detail_layers = [l for l in layers if isinstance(l,dict) and l.get("type")=="text" and float(l.get("size") or 16) <= 22]
    anchor = detail_layers[-1] if detail_layers else None
    if anchor and (re.search(r"\b\d{1,2}[:.]?\d{0,2}\s*(?:am|pm)\b", joined) or "time" in joined) and not any("time icon" in n for n in names):
        add({"type":"icon","name":"Time icon","icon":"clock","x":max(8,int(anchor.get("x") or 36)-24),"y":int(anchor.get("y") or h*.7),"w":16,"h":16,"color":accent,"opacity":1,"rotation":0}, first_text)
    if anchor and any(token in joined for token in ("venue", "location", "lagos", "abuja", "enugu", "road", "street", "centre", "center")) and not any("location icon" in n for n in names):
        add({"type":"icon","name":"Location icon","icon":"map-pin","x":max(8,int(anchor.get("x") or 36)-24),"y":int(anchor.get("y") or h*.7)+22,"w":16,"h":16,"color":accent,"opacity":1,"rotation":0}, first_text)
    if anchor and (re.search(r"(?:\+?234|0)\d[\d\s-]{7,}", joined) or "phone" in joined or "call" in joined) and not any("phone icon" in n for n in names):
        add({"type":"icon","name":"Phone icon","icon":"phone","x":max(8,int(anchor.get("x") or 36)-24),"y":min(h-26,int(anchor.get("y") or h*.7)+44),"w":16,"h":16,"color":accent,"opacity":1,"rotation":0}, first_text)
    if anchor and ("www." in joined or "http" in joined or ".com" in joined or ".org" in joined) and not any("web icon" in n for n in names):
        add({"type":"icon","name":"Web icon","icon":"globe","x":max(8,int(anchor.get("x") or 36)-24),"y":min(h-26,int(anchor.get("y") or h*.7)+66),"w":16,"h":16,"color":accent,"opacity":1,"rotation":0}, first_text)
    if anchor and any(token in joined for token in ("monday","tuesday","wednesday","thursday","friday","saturday","sunday","jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec")) and not any("date icon" in n for n in names):
        add({"type":"icon","name":"Date icon","icon":"calendar","x":max(8,int(anchor.get("x") or 36)-24),"y":max(10,int(anchor.get("y") or h*.7)-22),"w":16,"h":16,"color":accent,"opacity":1,"rotation":0}, first_text)

    # If the model still returned a skeletal direction, complete the visual system
    # with quiet structural anchors. These stay behind text and never invent copy.
    completion_candidates = [
        {"type":"shape","name":"Footer surface","kind":"rect","fill":"solid","x":0,"y":round(h*.82),"w":w,"h":round(h*.18),"color":dark,"opacity":0.16,"rotation":0},
        {"type":"shape","name":"Top micro rule","kind":"line","fill":"solid","x":round(w*.08),"y":round(h*.075),"w":round(w*.11),"h":2,"color":accent,"opacity":0.9,"rotation":0},
        {"type":"shape","name":"Corner geometry","kind":"triangle","fill":"solid","x":round(w*.82),"y":round(h*.84),"w":round(w*.18),"h":round(h*.16),"color":accent,"opacity":0.18,"rotation":0},
        {"type":"shape","name":"Tonal depth panel","kind":"rounded","fill":"solid","x":round(w*.055),"y":round(h*.64),"w":round(w*.89),"h":round(h*.19),"color":light,"opacity":0.045,"radius":"14px","stroke_color":light,"stroke_width":1,"rotation":0},
        {"type":"shape","name":"Secondary rhythm rule","kind":"line","fill":"solid","x":round(w*.74),"y":round(h*.11),"w":round(w*.16),"h":2,"color":light,"opacity":0.35,"rotation":0},
    ]
    for candidate in completion_candidates:
        if len(layers) + len(additions) >= MIN_FIRST_PASS_LAYERS:
            break
        add(candidate, first_text)

    # Insert in stable order while keeping all additions behind text.
    for offset, (pos, layer) in enumerate(additions):
        layers.insert(min(len(layers), pos + offset), layer)
    if additions:
        design["quality"] = design_quality_summary(design)
        return design, [f"Clyp added {len(additions)} editable art-direction layers because the first composition was too sparse."]
    return design, []




def ensure_semantic_finishing(design: dict[str, Any], brief: str) -> tuple[dict[str, Any], list[str]]:
    """Add communication-driven finishing roles even when the model already hit a layer quota.

    Density alone is not quality. This pass adds only semantic grouping/icons and category
    atmosphere that can be justified by supplied copy; it never invents facts.
    """
    layers=design.setdefault("layers",[])
    canvas=design.get("canvas") or {}
    w=int(canvas.get("width") or 432); h=int(canvas.get("height") or 540)
    pal=design.get("palette") or {}
    accent=safe_hex(pal.get("accent"),"#F0B429"); light=safe_hex(pal.get("light"),"#FFF4E6"); dark=safe_hex(pal.get("dark"),"#120302")
    category=infer_design_category(brief)
    names={str(l.get("name") or "").lower() for l in layers if isinstance(l,dict)}
    text_layers=[l for l in layers if isinstance(l,dict) and l.get("type")=="text"]
    first_text=next((i for i,l in enumerate(layers) if isinstance(l,dict) and l.get("type")=="text"),len(layers))
    additions=[]

    def add(layer,front=False):
        lname=str(layer.get("name") or "").lower()
        if lname in names:return
        names.add(lname);additions.append((front,layer))

    has_image=any(isinstance(l,dict) and l.get("type")=="image" and (l.get("src") or l.get("asset")) for l in layers)
    if has_image and not any("readability" in n or "copy fade" in n for n in names):
        copy_side=dominant_text_side(design)
        add({"type":"shape","name":"Copy readability fade","kind":"rect","fill":"linear","x":0,"y":0,"w":w,"h":h,"color":dark,"color2":dark,"gradient_angle":90 if copy_side=="left" else 270,"opacity":0.36,"rotation":0})
    if category in {"worship","music"} and not any("stage glow" in n or "warm atmosphere" in n for n in names):
        add({"type":"shape","name":"Warm stage glow","kind":"ellipse","fill":"radial","x":round(w*.55),"y":-70,"w":round(w*.62),"h":round(w*.62),"color":"#FFB14A","color2":dark,"opacity":0.22,"rotation":0,"shadow_color":"#FF9E3D","shadow_opacity":0.28,"shadow_blur":90})

    def find_text(predicate):
        return next((l for l in text_layers if predicate(str(l.get("name") or "").lower(),str(l.get("text") or "").lower())),None)
    date_l=find_text(lambda n,t:"date" in n or any(d in t for d in ("sunday","monday","tuesday","wednesday","thursday","friday","saturday")))
    time_l=find_text(lambda n,t:"time" in n or bool(re.search(r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b",t,re.I)))
    venue_l=find_text(lambda n,t:"venue" in n or "location" in n or any(k in t for k in ("lagos","abuja","enugu","centre","center","road","street")))
    phone_l=find_text(lambda n,t:"contact" in n or "phone" in n or bool(re.search(r"(?:\+?234|0)\d[\d\s-]{7,}",t)))
    icon_specs=[("Date detail icon","calendar",date_l),("Time detail icon","clock",time_l),("Venue detail icon","map-pin",venue_l),("Contact detail icon","phone",phone_l)]
    for name,icon,target in icon_specs:
        if not target or any(name.lower() in n for n in names):continue
        tx=int(target.get("x") or 36);ty=int(target.get("y") or 36)
        if tx>=38:
            add({"type":"icon","name":name,"icon":icon,"x":max(18,tx-22),"y":ty+1,"w":14,"h":14,"color":accent,"opacity":1,"rotation":0},front=True)

    # Group CTA/contact into a final intentional footer unit when both are present.
    cta=find_text(lambda n,t:"cta" in n or any(k in t for k in ("come ","book now","register","shop now","learn more","join us","get started","leave transformed")))
    if cta and phone_l and not any("cta footer" in n or "contact footer" in n for n in names):
        group=[cta,phone_l]
        gx=max(18,min(int(l.get("x") or 0) for l in group)-12); gy=max(18,min(int(l.get("y") or 0) for l in group)-8)
        gr=min(w-18,max(int(l.get("x") or 0)+int(l.get("w") or 0) for l in group)+12)
        gb=min(h-12,max(int(l.get("y") or 0)+max(int(l.get("h") or 0),_estimated_text_height(l)) for l in group)+8)
        add({"type":"shape","name":"CTA footer surface","kind":"rounded","fill":"solid","x":gx,"y":gy,"w":max(80,gr-gx),"h":max(42,gb-gy),"color":dark,"opacity":0.38,"radius":"10px","stroke_color":accent,"stroke_width":0.8,"rotation":0})

    # Insert background finishing just before text, icons just after the background group.
    backgrounds=[l for front,l in additions if not front]; fronts=[l for front,l in additions if front]
    for off,l in enumerate(backgrounds):layers.insert(min(len(layers),first_text+off),l)
    # after inserting background layers, locate first text again and place icons immediately before text
    first_text2=next((i for i,l in enumerate(layers) if isinstance(l,dict) and l.get("type")=="text"),len(layers))
    for off,l in enumerate(fronts):layers.insert(min(len(layers),first_text2+off),l)
    warnings=[]
    if additions:warnings.append(f"Clyp added {len(additions)} semantic finishing layers for information grouping, readability and art direction.")
    return design,warnings


def _estimated_text_height(layer: dict[str, Any]) -> int:
    text=str(layer.get("text") or "")
    size=max(6.0,float(layer.get("size") or 16))
    line=max(.72,float(layer.get("line") or 1.05))
    width=max(12.0,float(layer.get("w") or 120))
    font=str(layer.get("font") or "").lower()
    char_factor=.46 if any(k in font for k in ("condensed","bebas","oswald","teko","narrow","big shoulders")) else .53
    approx_per_line=max(4,int(width/max(1.0,size*char_factor)))
    lines=0
    for raw_line in text.split("\n") or [""]:
        # Word wrapping is only an estimate, but it catches the most common boxes that
        # are too short and therefore visually collide with the next layer.
        length=max(1,len(raw_line.strip()))
        lines += max(1,(length + approx_per_line - 1)//approx_per_line)
    return max(int(size*line*lines + 4), int(size*1.05))


def _horizontal_overlap(a: dict[str, Any], b: dict[str, Any]) -> float:
    left=max(float(a.get("x") or 0),float(b.get("x") or 0))
    right=min(float(a.get("x") or 0)+float(a.get("w") or 0),float(b.get("x") or 0)+float(b.get("w") or 0))
    return max(0.0,right-left)


def _text_overlaps(design: dict[str, Any]) -> list[tuple[int,int]]:
    layers=design.get("layers") or []
    text=[(i,l) for i,l in enumerate(layers) if isinstance(l,dict) and l.get("type")=="text" and str(l.get("text") or "").strip()]
    collisions=[]
    for pos,(i,a) in enumerate(text):
        ax=float(a.get("x") or 0); ay=float(a.get("y") or 0); aw=float(a.get("w") or 0); ah=float(a.get("h") or 0)
        for j,b in text[pos+1:]:
            bx=float(b.get("x") or 0); by=float(b.get("y") or 0); bw=float(b.get("w") or 0); bh=float(b.get("h") or 0)
            hov=max(0,min(ax+aw,bx+bw)-max(ax,bx))
            vov=max(0,min(ay+ah,by+bh)-max(ay,by))
            if hov > max(10,min(aw,bw)*.16) and vov > 2:
                collisions.append((i,j))
    return collisions


def layout_diagnostics(design: dict[str, Any]) -> dict[str, Any]:
    canvas=design.get("canvas") or {}
    w=float(canvas.get("width") or 432); h=float(canvas.get("height") or 540)
    margin=max(16,round(min(w,h)*.045))
    edges=[]
    for i,l in enumerate(design.get("layers") or []):
        if not isinstance(l,dict) or l.get("type")!="text":
            continue
        x=float(l.get("x") or 0); y=float(l.get("y") or 0); lw=float(l.get("w") or 0); lh=float(l.get("h") or 0)
        if x < 0 or y < 0 or x+lw > w or y+lh > h:
            edges.append(i)
        elif float(l.get("size") or 16) <= 24 and (x < margin*.55 or x+lw > w-margin*.55 or y+lh > h-margin*.45):
            edges.append(i)
    return {"text_overlaps":_text_overlaps(design),"text_edge_violations":edges}


def repair_layout_geometry(design: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Final deterministic preflight for the common AI geometry mistakes.

    It does not redesign the composition. It repairs text box height, obvious text/text
    collisions and canvas-edge clipping so details/CTA/contact cannot land on top of one another.
    """
    layers=design.get("layers") or []
    canvas=design.get("canvas") or {}
    w=int(canvas.get("width") or 432); h=int(canvas.get("height") or 540)
    margin=max(18,round(min(w,h)*.05))
    text_indices=[i for i,l in enumerate(layers) if isinstance(l,dict) and l.get("type")=="text" and str(l.get("text") or "").strip()]
    if not text_indices:
        return design,[]
    changed=False
    # Make text boxes tall enough for their own copy and keep non-display copy inside safe edges.
    for i in text_indices:
        l=layers[i]
        expected=_estimated_text_height(l)
        if int(l.get("h") or 0) < expected:
            l["h"]=expected; changed=True
        size=float(l.get("size") or 16)
        local_margin=max(12,round(margin*.65)) if size>=34 else margin
        if l.get("x",0) < local_margin:
            l["x"]=local_margin; changed=True
        max_w=max(20,w-local_margin-int(l.get("x") or 0))
        if int(l.get("w") or 0) > max_w:
            l["w"]=max_w; changed=True
        if l.get("y",0) < max(10,round(local_margin*.55)):
            l["y"]=max(10,round(local_margin*.55)); changed=True

    # Resolve collisions top-to-bottom. When a text block must move, move the rest of
    # the lower text stack with it so CTA/contact relationships remain intact.
    for _ in range(3):
        ordered=sorted(text_indices,key=lambda i:(float(layers[i].get("y") or 0),i))
        collision_fixed=False
        for pos,i in enumerate(ordered):
            cur=layers[i]
            cy=float(cur.get("y") or 0)
            blockers=[]
            for j in ordered[:pos]:
                prev=layers[j]
                if _horizontal_overlap(prev,cur) <= max(10,min(float(prev.get("w") or 0),float(cur.get("w") or 0))*.16):
                    continue
                pb=float(prev.get("y") or 0)+float(prev.get("h") or 0)
                if cy < pb+5:
                    blockers.append(pb)
            if not blockers:
                continue
            desired=max(blockers)+max(6,round(min(float(cur.get("size") or 16),18)*.42))
            delta=desired-cy
            if delta <= 0:
                continue
            for k in ordered[pos:]:
                layers[k]["y"]=round(float(layers[k].get("y") or 0)+delta)
            collision_fixed=True; changed=True
            break
        if not collision_fixed:
            break

    # If the lower information stack was pushed beyond the canvas, move that stack up
    # together instead of letting the final contact line clip or overlap the CTA.
    max_bottom=max(float(layers[i].get("y") or 0)+float(layers[i].get("h") or 0) for i in text_indices)
    allowed_bottom=h-margin
    overflow=max_bottom-allowed_bottom
    if overflow>0:
        lower=[i for i in text_indices if float(layers[i].get("y") or 0)>=h*.48]
        upper=[i for i in text_indices if i not in lower]
        if lower:
            min_lower=min(float(layers[i].get("y") or 0) for i in lower)
            upper_bottom=max([float(layers[i].get("y") or 0)+float(layers[i].get("h") or 0) for i in upper] or [margin])
            max_up=max(0,min_lower-(upper_bottom+8))
            shift=min(overflow+2,max_up)
            if shift>0:
                for i in lower:
                    layers[i]["y"]=round(float(layers[i].get("y") or 0)-shift)
                changed=True

    # If anything still extends past the safe bottom, shift text as a group. Never
    # clamp several independent lines to the same Y coordinate — that was the source
    # of the old CTA/contact overlap bug.
    max_bottom=max(float(layers[i].get("y") or 0)+float(layers[i].get("h") or 0) for i in text_indices)
    overflow=max(0.0,max_bottom-(h-margin*.45))
    if overflow>0:
        min_top=min(float(layers[i].get("y") or 0) for i in text_indices)
        shift=min(overflow+2,max(0,min_top-10))
        if shift>0:
            for i in text_indices:
                layers[i]["y"]=round(float(layers[i].get("y") or 0)-shift)
            changed=True

    # One last collision pass after all bottom-edge movement. This preserves a real
    # gap between CTA and contact instead of fixing clipping by stacking them.
    for _ in range(3):
        ordered=sorted(text_indices,key=lambda i:(float(layers[i].get("y") or 0),i))
        fixed=False
        for pos,i in enumerate(ordered):
            cur=layers[i]; cy=float(cur.get("y") or 0)
            blockers=[]
            for j in ordered[:pos]:
                prev=layers[j]
                if _horizontal_overlap(prev,cur) <= max(10,min(float(prev.get("w") or 0),float(cur.get("w") or 0))*.16):
                    continue
                pb=float(prev.get("y") or 0)+float(prev.get("h") or 0)
                if cy < pb+5: blockers.append(pb)
            if not blockers: continue
            desired=max(blockers)+max(5,round(min(float(cur.get("size") or 16),18)*.36))
            delta=desired-cy
            if delta<=0: continue
            for k in ordered[pos:]: layers[k]["y"]=round(float(layers[k].get("y") or 0)+delta)
            fixed=True; changed=True; break
        if not fixed: break

    # If the second collision pass pushed the lower stack down again, shift the lower
    # stack upward together, maintaining its internal spacing.
    max_bottom=max(float(layers[i].get("y") or 0)+float(layers[i].get("h") or 0) for i in text_indices)
    overflow=max(0.0,max_bottom-(h-margin*.45))
    if overflow>0:
        lower=[i for i in text_indices if float(layers[i].get("y") or 0)>=h*.45]
        upper=[i for i in text_indices if i not in lower]
        if lower:
            lower_top=min(float(layers[i].get("y") or 0) for i in lower)
            upper_bottom=max([float(layers[i].get("y") or 0)+float(layers[i].get("h") or 0) for i in upper] or [10])
            shift=min(overflow+2,max(0,lower_top-(upper_bottom+7)))
            if shift>0:
                for i in lower: layers[i]["y"]=round(float(layers[i].get("y") or 0)-shift)
                changed=True

    remaining=layout_diagnostics(design)
    warnings=[]
    if changed:
        warnings.append("Clyp automatically repaired text spacing and canvas-edge collisions before opening the editor.")
    if remaining["text_overlaps"]:
        warnings.append("Clyp detected a complex intentional/ambiguous text overlap; review those layers in the editor.")
    design["layout_diagnostics"]=remaining
    return design,warnings


def closest_image_ratio(width: int, height: int) -> str:
    ratio = width / max(1, height)
    choices = {"1:1": 1.0, "2:3": 2/3, "3:2": 3/2, "3:4": .75, "4:3": 4/3, "4:5": .8, "5:4": 1.25, "9:16": 9/16, "16:9": 16/9}
    return min(choices, key=lambda k: abs(choices[k] - ratio))


def _quota_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "429" in text or "resource_exhausted" in text or "quota exceeded" in text or "rate limit" in text


def _compact_stock_query(text: str) -> str:
    raw = re.sub(r"#[0-9a-fA-F]{6}", " ", text or "")
    raw = re.sub(r"[^a-zA-Z0-9\s-]", " ", raw.lower())
    stop = {
        "create","professional","design","flyer","poster","visual","asset","only","with","without","the","and","for","from","this","that","use","using","toward","left","right","center","background","negative","space","editable","typography","words","captions","logo","layout","colour","color","palette","premium","realistic","photo","photography","image","hero","cinematic","modern","high","impact","subtle","controlled"
    }
    tokens=[]
    for tok in raw.split():
        if len(tok) < 3 or tok in stop or tok.isdigit():
            continue
        if tok not in tokens:
            tokens.append(tok)
        if len(tokens) >= 7:
            break
    return " ".join(tokens) or "people event"


def _stock_query_variants(query: str, brief: str = "") -> list[str]:
    """Generate a few concrete stock queries instead of trusting one vague AI phrase."""
    combined = f"{query} {brief}".strip()
    base = _compact_stock_query(combined)
    category = infer_design_category(combined)
    text = combined.lower()
    variants = [base]
    if category == "worship":
        african = "african " if "afric" in text or "nigerian" in text else ""
        variants += [
            f"{african}church worship congregation people",
            f"{african}worshippers church service stage",
            f"{african}church congregation worship people",
        ]
    elif category == "food":
        variants += ["restaurant food plated meal", "food close up restaurant", "chef restaurant food"]
    elif category == "beauty":
        variants += ["beauty portrait skincare model", "editorial beauty portrait", "skincare woman portrait"]
    elif category == "real-estate":
        variants += ["modern luxury house exterior", "modern apartment interior", "real estate property home"]
    elif category == "technology":
        variants += ["technology office people", "software team modern office", "technology abstract workspace"]
    elif category == "music":
        variants += ["concert audience stage lights", "music performance crowd", "live concert people stage"]
    elif category == "corporate":
        variants += ["business people modern office", "professional conference speaker", "business meeting people"]
    elif category == "sale":
        variants += ["retail product shopping", "shopping product promotion", "store retail products"]
    # preserve order, remove duplicates and overly long phrases
    out=[]
    for q in variants:
        q=re.sub(r"\s+", " ", q).strip()[:120]
        if q and q not in out:
            out.append(q)
    return out[:4]


def _openverse_item_text(item: dict[str, Any]) -> str:
    pieces=[str(item.get("title") or ""), str(item.get("creator") or ""), str(item.get("source") or "")]
    for tag in item.get("tags") or []:
        if isinstance(tag, dict):
            pieces.append(str(tag.get("name") or ""))
        else:
            pieces.append(str(tag))
    return " ".join(pieces).lower()


def _stock_relevance_score(item: dict[str, Any], desired_text: str, category: str, canvas_ratio: float) -> float:
    hay=_openverse_item_text(item)
    desired=[t for t in _compact_stock_query(desired_text).split() if len(t)>=3]
    score=0.0
    for token in desired:
        if token in hay:
            score += 3.0
    # Category-specific visual semantics. These rules deliberately prefer complete scenes
    # over isolated objects when the design asks for people/emotion.
    rewards={
        "worship": ("worship","church","congregation","people","crowd","service","praise","stage","audience","christian"),
        "food": ("food","restaurant","meal","dish","plate","chef","cuisine"),
        "beauty": ("beauty","portrait","skin","skincare","model","face","fashion"),
        "real-estate": ("house","home","property","apartment","interior","architecture"),
        "technology": ("technology","computer","office","software","team","digital"),
        "music": ("concert","music","crowd","stage","audience","performance"),
        "corporate": ("business","office","conference","professional","meeting","speaker"),
    }.get(category, ())
    score += sum(2.1 for t in rewards if t in hay)
    if category in {"worship","music","corporate"}:
        penalties=("microphone closeup","microphone only","hand only","hands only","book only","instrument only","guitar only","object","still life")
        score -= sum(5.0 for p in penalties if p in hay)
        # Individual object words are a lighter penalty when there is no evidence of a crowd/people scene.
        if not any(t in hay for t in ("people","crowd","congregation","audience","person","woman","man","group")):
            score -= sum(1.8 for t in ("microphone","hand","book","guitar","instrument") if t in hay)
    w=int(item.get("width") or 0); h=int(item.get("height") or 0)
    if w>=1200 and h>=800: score += 2.5
    elif w>=800 and h>=600: score += 1.4
    if item.get("creator"): score += .5
    if w>0 and h>0:
        ratio=w/h
        # Prefer imagery that crops to the canvas without throwing away most of the scene.
        ratio_delta=abs(ratio-canvas_ratio)
        score += max(0.0, 2.0-ratio_delta*2.2)
    return score


def _fetch_candidate_thumbnail(item: dict[str, Any]) -> tuple[bytes, str] | None:
    url=str(item.get("thumbnail") or item.get("url") or "").strip()
    if not url.startswith(("http://","https://")):
        return None
    req=urllib.request.Request(url, headers={"Accept":"image/*","User-Agent":"Clyp-Design-Studio/5.1"})
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            mime=response.headers.get_content_type() or "image/jpeg"
            if not mime.startswith("image/"):
                return None
            data=response.read(900_000)
            if not data:
                return None
            return data,mime
    except Exception:
        return None


def _vision_choose_stock(candidates: list[dict[str, Any]], brief: str, design: dict[str, Any] | None) -> int | None:
    """Use the existing Gemini vision-capable design model as an art-director reranker.

    If this call is unavailable/quota-limited, metadata scoring still works. A candidate may
    also be rejected entirely so Clyp shows a placeholder instead of a visibly wrong photo.
    """
    enabled=os.getenv("CLYP_VISION_STOCK_RERANK","1").strip().lower() not in {"0","false","no","off"}
    if not enabled or not candidates or types is None or not API_KEY:
        return None
    parts=[]
    copy_side=dominant_text_side(design or {}) if design else "left"
    parts.append(types.Part.from_text(text=(
        "You are Clyp's photo editor. Choose the ONE candidate that best fits the design brief. "
        "Prioritise the requested subject and emotional scene, professional photographic quality, useful crop/negative space, believable people, and no prominent watermark/text. "
        "For people-led event/worship briefs, reject isolated close-ups of hands, microphones, books or instruments when the brief calls for worshippers/congregation. "
        f"Typography is mainly on the {copy_side}, so useful subject placement away from that zone is a plus. "
        "Return JSON only as {\"index\": <integer>, \"accept\": true|false}. If none genuinely fit, set accept=false and index=-1.\n"
        f"Brief: {brief[:2500]}"
    )))
    mapped=[]
    for i,item in enumerate(candidates[:7]):
        thumb=_fetch_candidate_thumbnail(item)
        if not thumb:
            continue
        data,mime=thumb
        parts.append(types.Part.from_text(text=f"Candidate {i}: {item.get('title') or 'Untitled'}"))
        parts.append(types.Part.from_bytes(data=data,mime_type=mime))
        mapped.append(i)
    if not mapped:
        return None
    client=get_client()
    try:
        response=client.models.generate_content(
            model=MODEL,
            contents=[types.Content(role="user",parts=parts)],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.05,
                max_output_tokens=200,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        result=parse_json_response(response.text or "")
        if not bool(result.get("accept")):
            return -1
        idx=int(result.get("index",-1))
        return idx if 0 <= idx < len(candidates) else -1
    except Exception:
        return None
    finally:
        client.close()


def search_openverse_asset(query: str, brief: str = "", design: dict[str, Any] | None = None) -> dict[str, Any] | None:
    if not STOCK_FALLBACK_ENABLED:
        return None
    canvas=design.get("canvas") if isinstance(design,dict) else {}
    cw=float((canvas or {}).get("width") or 432); ch=float((canvas or {}).get("height") or 540)
    canvas_ratio=cw/max(1.0,ch)
    desired=f"{query} {brief}".strip()
    category=infer_design_category(desired)
    seen=set(); candidates=[]
    for q in _stock_query_variants(query,brief):
        params=urllib.parse.urlencode({"q":q,"page_size":24})
        req=urllib.request.Request(f"{OPENVERSE}?{params}",headers={"Accept":"application/json","User-Agent":"Clyp-Design-Studio/5.1"})
        try:
            with urllib.request.urlopen(req,timeout=12) as response:
                data=json.loads(response.read().decode("utf-8"))
        except Exception:
            continue
        for item in data.get("results") or []:
            if item.get("mature"):
                continue
            url=str(item.get("url") or item.get("thumbnail") or "").strip()
            if not url.startswith(("http://","https://")):
                continue
            ident=str(item.get("id") or url)
            if ident in seen:
                continue
            seen.add(ident)
            score=_stock_relevance_score(item,desired,category,canvas_ratio)
            candidates.append({"score":score,"item":item,"url":url,"query":q})
    if not candidates:
        return None
    candidates.sort(key=lambda c:c["score"],reverse=True)
    top=candidates[:9]
    vision_idx=_vision_choose_stock([c["item"] for c in top], brief or query, design)
    if vision_idx == -1:
        return None
    choice=top[vision_idx] if isinstance(vision_idx,int) and 0 <= vision_idx < len(top) else top[0]
    # Reject very weak metadata matches instead of returning an obviously unrelated photograph.
    if vision_idx is None and choice["score"] < 2.2:
        return None
    item,url=choice["item"],choice["url"]
    proxied="/api/assets/fetch?url="+urllib.parse.quote(url,safe="")
    return {
        "src":proxied,
        "source_kind":"online",
        "stock_query":choice["query"],
        "stock_relevance_score":round(float(choice["score"]),2),
        "attribution":{
            "provider":"Openverse",
            "title":item.get("title") or "Untitled image",
            "creator":item.get("creator") or "Unknown creator",
            "license":item.get("license") or "",
            "license_url":item.get("license_url") or "",
            "landing_url":item.get("foreign_landing_url") or item.get("detail_url") or "",
            "attribution":item.get("attribution") or "",
        },
    }


def generate_image_asset(prompt: str, width: int = 1024, height: int = 1024) -> str:
    """Generate one visual asset. Typography/layout stays in structured Clyp layers."""
    if not prompt.strip():
        raise RuntimeError("Image prompt is required")
    if types is None:
        raise RuntimeError("google-genai is not installed. Run: py -m pip install -r requirements.txt")
    art_prompt = (
        "Create ONLY the visual asset for a professional graphic design, with no poster layout, no headline, no captions, "
        "no logo and no UI. Make it compositionally useful inside a flyer. "
        "Use professional lighting, believable materials/skin/product detail, controlled colour and deliberate negative space. "
        "Avoid generic AI glow unless requested. Asset brief: " + prompt.strip()
    )
    last_error: Exception | None = None
    models=[]
    for name in (IMAGE_MODEL, IMAGE_FALLBACK_MODEL):
        name = _IMAGE_MODEL_ALIASES.get(name, name)
        if name and name not in models:
            models.append(name)
    for model_name in models:
        client = get_client()
        try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[art_prompt],
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                        response_format={"image": {"aspect_ratio": closest_image_ratio(width, height), "image_size": "1K"}},
                    ),
                )
            except (TypeError, ValueError):
                response = client.models.generate_content(
                    model=model_name,
                    contents=[art_prompt],
                    config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
                )
            for part in response.parts or []:
                blob = getattr(part, "inline_data", None)
                if blob is None:
                    continue
                data = getattr(blob, "data", None)
                mime = getattr(blob, "mime_type", None) or "image/png"
                if not data:
                    continue
                encoded = data if isinstance(data, str) else base64.b64encode(bytes(data)).decode("ascii")
                return f"data:{mime};base64,{encoded}"
            last_error = RuntimeError(f"{model_name} returned no image asset.")
        except Exception as exc:
            last_error = exc
            # A zero/paid-only quota will not be fixed by immediately hammering another
            # preview alias. Continue only to a genuinely different configured model.
        finally:
            client.close()
    raise RuntimeError(f"Image generation failed: {last_error}")

def hydrate_generated_assets(design: dict[str, Any], max_assets: int = 1) -> list[str]:
    assets = design.setdefault("assets", {})
    warnings: list[str] = []
    generated = 0
    for idx, layer in enumerate(design.get("layers") or []):
        if generated >= max_assets or not isinstance(layer, dict) or layer.get("type") != "image":
            continue
        prompt = str(layer.get("asset_prompt") or "").strip()
        if not prompt:
            continue
        key = f"ai_asset_{generated + 1}"
        try:
            assets[key] = generate_image_asset(prompt, int(layer.get("w") or 432), int(layer.get("h") or 540))
            layer["asset"] = key
            layer["source_kind"] = "ai"
            layer.pop("src", None)
            generated += 1
        except Exception as exc:
            warnings.append(f"Image asset could not be generated: {exc}")
    return warnings


IMAGERY_REQUIRED_PATTERNS = (
    "realistic image", "realistic photo", "photograph", "photography", "photo of",
    "image of", "picture of", "portrait of", "people", "person", "worshipper",
    "worshippers", "model", "product photo", "product shot", "food photo",
    "illustration", "illustrated", "3d render", "render of", "hero image",
    "background image", "cinematic", "editorial image", "lifestyle image",
)


def brief_requests_imagery(brief: str) -> bool:
    text = re.sub(r"\s+", " ", (brief or "").lower())
    return any(token in text for token in IMAGERY_REQUIRED_PATTERNS)


def dominant_text_side(design: dict[str, Any]) -> str:
    width = max(1, int(design.get("canvas", {}).get("width", 432)))
    text_layers = [l for l in design.get("layers", []) if isinstance(l, dict) and l.get("type") == "text"]
    if not text_layers:
        return "left"
    weighted = []
    for l in text_layers:
        x = float(l.get("x") or 0)
        w = float(l.get("w") or 80)
        size = float(l.get("size") or 16)
        weighted.append(((x + w / 2) / width, max(1.0, size)))
    avg = sum(pos * weight for pos, weight in weighted) / sum(weight for _, weight in weighted)
    if avg < .46:
        return "left"
    if avg > .54:
        return "right"
    return "center"


def build_fallback_asset_prompt(brief: str, design: dict[str, Any]) -> str:
    palette = design.get("palette") or {}
    copy_side = dominant_text_side(design)
    subject_side = "right" if copy_side == "left" else "left" if copy_side == "right" else "center/right"
    dark = palette.get("dark") or design.get("canvas", {}).get("bg") or "#17100f"
    accent = palette.get("accent") or "#d6a62a"
    dominant = palette.get("dominant") or dark
    return (
        f"Create the hero visual required by this design brief: {brief}. "
        f"This is a visual asset only, never a finished flyer. Place the main subject toward the {subject_side} "
        f"and preserve useful negative space on the {copy_side} for editable typography. "
        f"Art-direct the scene around a sophisticated palette related to {dominant}, {dark}, and accent {accent}. "
        "Use believable professional lighting, depth, foreground/background separation, natural skin/material detail, "
        "controlled highlights and shadows, and a premium campaign-photography finish. "
        "No words, no captions, no logo, no poster layout, no decorative text, no UI."
    )


def _apply_stock_to_layer(layer: dict[str, Any], query: str, brief: str = "", design: dict[str, Any] | None = None) -> dict[str, Any] | None:
    asset = search_openverse_asset(query, brief=brief, design=design)
    if not asset:
        return None
    layer.update(asset)
    layer.pop("asset", None)
    return asset


def ensure_required_hero_image(design: dict[str, Any], brief: str) -> tuple[bool, list[str]]:
    """Guarantee useful imagery without allowing image quota to block the whole design.

    Priority: Gemini image -> openly licensed online image -> styled placeholder layer.
    """
    required = brief_requests_imagery(brief)
    warnings: list[str] = []
    image_layers = [l for l in design.get("layers", []) if isinstance(l, dict) and l.get("type") == "image"]

    if image_layers:
        warnings.extend(hydrate_generated_assets(design, max_assets=1))
        hydrated = [l for l in image_layers if l.get("asset") or l.get("src")]
        if hydrated:
            return required, warnings
        target = image_layers[0]
        query = str(target.get("stock_query") or target.get("asset_prompt") or brief)
        stock = _apply_stock_to_layer(target, query, brief=brief, design=design)
        if stock:
            warnings.append(
                "AI image quota was unavailable, so Clyp continued with an openly licensed Openverse image. Attribution is retained on the image layer."
            )
            return required, warnings
        if required:
            target.update({
                "source_kind": "placeholder", "src": "", "fit": "cover",
                "brightness": 1, "contrast": 1, "saturation": 1,
                "name": "Add hero image", "placeholder": True,
            })
            warnings.append("Clyp could not reach an AI or online image source. The layout is preserved; add a local image from the Images panel.")
        return required, warnings

    if not required:
        return False, []

    canvas = design.get("canvas") or {}
    width = max(128, int(canvas.get("width") or 432))
    height = max(128, int(canvas.get("height") or 540))
    prompt = build_fallback_asset_prompt(brief, design)
    hero = {
        "type": "image", "name": "Hero image", "x": 0, "y": 0, "w": width, "h": height,
        "opacity": 1, "rotation": 0, "source_kind": "ai", "asset_prompt": prompt,
        "stock_query": _compact_stock_query(brief), "fit": "cover", "blend_mode": "normal", "mask": "none",
        "brightness": .74, "contrast": 1.12, "saturation": 1.06, "blur": 0,
        "focal_x": 68 if dominant_text_side(design) == "left" else 32 if dominant_text_side(design) == "right" else 55,
        "focal_y": 50, "radius": "0"
    }
    try:
        hero["src"] = generate_image_asset(prompt, width, height)
    except Exception as exc:
        stock = _apply_stock_to_layer(hero, hero["stock_query"], brief=brief, design=design)
        if stock:
            warnings.append(
                "AI image generation is unavailable for the current Gemini quota, so Clyp automatically used an openly licensed Openverse image and retained its attribution."
            )
        else:
            hero["source_kind"] = "placeholder"
            hero["placeholder"] = True
            hero["src"] = ""
            warnings.append(
                "AI image generation is unavailable and no suitable online image was reachable. Clyp kept the composition and inserted an image placeholder; use Images → Upload or Online to replace it."
            )
    design.setdefault("layers", []).insert(0, hero)
    return True, warnings

def call_json(contents: Any, system_instruction: str, output_rules: str, temperature: float = 0.35) -> dict[str, Any]:
    client = get_client()
    if types is None:
        raise RuntimeError("google-genai is not installed. Run: py -m pip install -r requirements.txt")
    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=f"{system_instruction}\n\n{output_rules}",
                response_mime_type="application/json",
                temperature=temperature,
                max_output_tokens=12288,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        return parse_json_response(response.text or "")
    finally:
        client.close()


SYSTEM_DESIGNER = f"""You are Clyp's senior graphic designer and art director working inside an editable design editor.
Your job is to create professional, visually distinctive flyers/posters for non-designers while keeping every practical element editable.
Do not default to a generic SaaS/AI aesthetic. Match the design language to the audience, message and category.

{DESIGN_PLAYBOOK}

{FEW_SHOT_PATTERNS}

Every returned layer must be independently editable. Keep coordinates inside the canvas unless an intentional bleed is required.
Never invent critical factual information. If important facts are missing, use clearly neutral placeholders or omit them.
"""

SYSTEM_RECONSTRUCTOR = """You are Clyp's forensic flyer reconstruction engine. Your task is visual tracing, not redesign.
Study the uploaded source carefully and preserve its original composition, aspect ratio, hierarchy, palette, spacing, scale relationships and visual weight. Do NOT simplify a rich design into a generic poster. Do NOT improve or modernise the source. Match it.
Complex source imagery must be preserved as cropped image layers from the original upload rather than replaced with crude vector approximations. Photographs, faces, logos, icons, lighting rigs, glow effects, textured brush marks and detailed decorative graphics should normally become image crop layers. Text that is meant to be editable should become text layers with exact transcription and close typography/placement. Simple solid bars and blocks may become shapes.
The final layer stack must visually resemble the uploaded source before the user edits anything."""


@app.post("/generate")
def generate():
    if not authorised(request):
        return jsonify({"ok": False, "message": "unauthorised"}), 401
    started = time.perf_counter()
    try:
        data = request.get_json(force=True) or {}
        brief = str(data.get("brief") or "").strip()
        fmt = str(data.get("format") or "Instagram portrait · 1080 × 1350")
        if not brief:
            return jsonify({"ok": False, "message": "Brief is required"}), 422
        width, height, canonical = canvas_for_format(fmt)
        category = infer_design_category(brief)
        blueprint = category_blueprint(category)
        prompt = f"""<context>
User brief: {brief}
Working canvas: {width} by {height} editor units.
Intended export format: {canonical}.
Detected category: {category}.
Category blueprint: {blueprint}
</context>
<task>
Create a complete, professionally art-directed editable flyer/poster. Infer the category and mood from the brief. Build the hierarchy, palette, typography and composition deliberately. If the user explicitly asks for a photograph, realistic image, people, a model, product photography, illustration, or another hero visual, you MUST include one image layer with a precise asset_prompt; imagery is not optional in that case. Use gradients/shapes/effects only when they perform a visual job. Unless the brief explicitly asks for minimalism, do not stop at a background plus a few text blocks: create enough structured visual anchors, information grouping, accents, icons and depth to make the flyer feel finished at thumbnail size. Use concise real copy inferred from the brief; if a critical fact such as date, price, time, venue, phone or URL was not supplied, use a neutral placeholder or omit it rather than inventing facts.
</task>
<quality_gate>
Before output, silently review the result at full size and thumbnail size for hierarchy, colour harmony, text contrast, margins, alignment, proximity, balance, readability and unnecessary decoration. Confirm that no two independent text layers overlap, CTA/contact have a dedicated final zone, and every line stays inside the safe canvas area.
</quality_gate>"""
        raw = call_json(prompt, SYSTEM_DESIGNER, DESIGN_OUTPUT_RULES, temperature=0.45)
        design = normalise_design(raw, fmt, allow_images=True)

        # V5 quality gate: if the first pass is only a few text blocks, give the
        # design model one focused refinement pass before the user ever sees it.
        design, polish_note = polish_sparse_design(design, brief, fmt)

        imagery_required, warnings = ensure_required_hero_image(design, brief)
        if polish_note:
            warnings.append(polish_note)

        # Final deterministic guard. This never invents factual copy: it can only
        # add editable visual structure such as overlays, frames, rails, rules,
        # glows, patterns and fact-matched icons.
        design, density_warnings = enrich_sparse_design(design, brief)
        warnings.extend(density_warnings)

        # Repair AI text geometry before decorative grouping is calculated. Footer
        # surfaces/icons are therefore built around the final readable text positions,
        # not around coordinates that are about to move.
        design, layout_warnings = repair_layout_geometry(design)
        warnings.extend(layout_warnings)
        design, finishing_warnings = ensure_semantic_finishing(design, brief)
        warnings.extend(finishing_warnings)
        design, final_layout_warnings = repair_layout_geometry(design)
        warnings.extend(final_layout_warnings)
        warnings = list(dict.fromkeys(warnings))
        design["quality"] = design_quality_summary(design)
        return jsonify({"ok": True, "model": MODEL, "image_model": IMAGE_MODEL, "design": design, "critique": raw.get("critique", {}), "warnings": warnings, "imagery_required": imagery_required, "density": design_density_summary(design), "duration_ms": int((time.perf_counter() - started) * 1000)})
    except Exception as exc:
        return jsonify({"ok": False, "message": str(exc)}), 502


@app.post("/edit")
def edit():
    if not authorised(request):
        return jsonify({"ok": False, "message": "unauthorised"}), 401
    started = time.perf_counter()
    try:
        data = request.get_json(force=True) or {}
        command = str(data.get("command") or "").strip()
        current = data.get("design")
        if not command or not isinstance(current, dict):
            return jsonify({"ok": False, "message": "Command and current design are required"}), 422
        fmt = str(current.get("format") or data.get("format") or "1080 × 1350")
        prompt = (
            "Modify the existing editable design according to the user's instruction. Preserve everything that does not need to change. "
            "Image layers may reference asset='source_upload'; preserve those layers unless the user asks to remove or move them. Return the full revised editable design.\n\n"
            f"User instruction: {command}\n\nExisting design JSON:\n{json.dumps(current, ensure_ascii=False)}"
        )
        current_images = [l for l in current.get("layers", []) if isinstance(l, dict) and l.get("type") == "image"]
        source_trace = any(l.get("crop") or l.get("source_kind") == "source" for l in current_images)
        raw = call_json(prompt, SYSTEM_DESIGNER, RECONSTRUCTION_OUTPUT_RULES if source_trace else DESIGN_OUTPUT_RULES)
        design = normalise_design(raw, fmt, canvas_override=(int(current.get("canvas", {}).get("width", 432)), int(current.get("canvas", {}).get("height", 540))) if source_trace else None, allow_images=True)
        # The layout model should not have to echo large URLs/base64 assets. Reattach image
        # identity from the current structured design by name/order whenever it preserved an image.
        old_by_name = {str(l.get("name") or ""): l for l in current_images}
        old_remaining = list(current_images)
        for layer in design.get("layers", []):
            if layer.get("type") != "image":
                continue
            old = old_by_name.get(str(layer.get("name") or ""))
            if old is None and old_remaining:
                old = old_remaining.pop(0)
            if old:
                for key in ("asset", "src", "source_kind", "crop", "attribution", "asset_prompt", "stock_query"):
                    if old.get(key) is not None and not layer.get(key):
                        layer[key] = old.get(key)
        design["name"] = current.get("name") or design["name"]
        design["format"] = current.get("format") or design["format"]
        design, layout_warnings = repair_layout_geometry(design)
        return jsonify({"ok": True, "model": MODEL, "design": design, "critique": raw.get("critique", {}), "warnings": layout_warnings, "duration_ms": int((time.perf_counter() - started) * 1000)})
    except Exception as exc:
        return jsonify({"ok": False, "message": str(exc)}), 502



@app.post("/image-generate")
def image_generate():
    if not authorised(request):
        return jsonify({"ok": False, "message": "unauthorised"}), 401
    started = time.perf_counter()
    try:
        data = request.get_json(force=True) or {}
        prompt = str(data.get("prompt") or "").strip()
        width = clamp_int(data.get("width"), 128, 4096, 1024)
        height = clamp_int(data.get("height"), 128, 4096, 1024)
        if not prompt:
            return jsonify({"ok": False, "message": "Image prompt is required"}), 422
        try:
            data_url = generate_image_asset(prompt, width, height)
            return jsonify({"ok": True, "model": IMAGE_MODEL, "source_kind": "ai", "data_url": data_url, "duration_ms": int((time.perf_counter() - started) * 1000)})
        except Exception as exc:
            stock = search_openverse_asset(prompt, brief=prompt, design={"canvas":{"width":width,"height":height}})
            if stock:
                return jsonify({
                    "ok": True, "model": IMAGE_MODEL, "source_kind": "online",
                    "src": stock["src"], "attribution": stock.get("attribution"),
                    "stock_query": stock.get("stock_query"),
                    "warning": "AI image quota is unavailable, so Clyp used an openly licensed Openverse image instead.",
                    "duration_ms": int((time.perf_counter() - started) * 1000)
                })
            raise RuntimeError(f"AI image generation is unavailable and no online fallback was found: {exc}") from exc
    except Exception as exc:
        return jsonify({"ok": False, "message": str(exc)}), 502


@app.post("/reconstruct")
def reconstruct():
    if not authorised(request):
        return jsonify({"ok": False, "message": "unauthorised"}), 401
    started = time.perf_counter()
    try:
        data = request.get_json(force=True) or {}
        data_url = str(data.get("data_url") or "")
        filename = str(data.get("filename") or "uploaded design")
        source_w = clamp_int(data.get("source_width"), 0, 10000, 0)
        source_h = clamp_int(data.get("source_height"), 0, 10000, 0)
        if not data_url.startswith("data:") or ";base64," not in data_url:
            return jsonify({"ok": False, "message": "A base64 data URL is required"}), 422
        header, encoded = data_url.split(",", 1)
        mime = header[5:].split(";", 1)[0].strip() or "image/png"
        blob = base64.b64decode(encoded, validate=True)
        if len(blob) > 7 * 1024 * 1024:
            return jsonify({"ok": False, "message": "File is too large for this local MVP (7 MB max)."}), 413
        if types is None:
            raise RuntimeError("google-genai is not installed. Run: py -m pip install -r requirements.txt")

        canvas_w, canvas_h = reconstruction_canvas(source_w, source_h)
        aspect_note = f"The source is {source_w}×{source_h} pixels. Use an exact proportional working canvas of {canvas_w}×{canvas_h} editor units." if source_w and source_h else f"Use a working canvas of {canvas_w}×{canvas_h} editor units."
        prompt = (
            "Reconstruct this uploaded flyer as faithfully as possible. This is a source-matching task, not a creative reinterpretation.\n"
            f"{aspect_note}\n"
            "First identify major photographic/graphic zones, then exact editable text, then simple shapes. "
            "Preserve the original dark/light regions, photo coverage, title proportions, footer structure, logos/icons and decorative effects. "
            "For every photo/logo/icon/complex visual region that should be preserved from the source, create an image layer with a crop=[left,top,right,bottom] box using 0..1000 normalised source coordinates and x/y/w/h showing where that crop belongs on the working canvas. "
            "Do not replace a photograph with a circle or a flat colour. Do not replace a logo with placeholder text if it can be retained as an image crop. "
            "Transcribe visible editable text exactly, including line breaks where they matter. Match condensed/bold typography using the closest allowed font. "
            "Use back-to-front layer order. Fidelity is more important than having few layers."
        )
        raw = call_json([prompt, types.Part.from_bytes(data=blob, mime_type=mime)], SYSTEM_RECONSTRUCTOR, RECONSTRUCTION_OUTPUT_RULES, temperature=0.2)
        design = normalise_design(raw, canvas_override=(canvas_w, canvas_h), allow_images=True)
        design["name"] = Path(filename).stem[:190] or design["name"]
        design["format"] = f"Source · {source_w} × {source_h}" if source_w and source_h else f"Source · {canvas_w} × {canvas_h}"
        return jsonify({"ok": True, "model": MODEL, "design": design, "critique": raw.get("critique", {}), "duration_ms": int((time.perf_counter() - started) * 1000)})
    except Exception as exc:
        return jsonify({"ok": False, "message": str(exc)}), 502


@app.get("/health")
def health():
    return jsonify({
        "ok": True,
        "service": "clyp-ai",
        "python": True,
        "model": MODEL,
        "image_model": IMAGE_MODEL,
        "image_fallback_model": IMAGE_FALLBACK_MODEL,
        "stock_fallback": STOCK_FALLBACK_ENABLED,
        "auto_polish_sparse": AUTO_POLISH_SPARSE,
        "minimum_first_pass_layers": MIN_FIRST_PASS_LAYERS,
        "editor_contract": "v5.1-quality-preflight",
        "image_pipeline": "gemini-image -> relevance-ranked Openverse + Gemini vision rerank -> local placeholder",
        "gemini_configured": bool(API_KEY),
        "sdk_installed": genai is not None,
        "structured_output": "json-mime/no-response-schema",
        "thinking_budget": 0,
        "reconstruction": "source-aspect + editable text/shapes + source image crops",
        "design_brain": "professional-art-director-v5.1",
        "advanced_shapes": True,
        "generated_image_assets": True,
        "image_compositing": True,
    })


if __name__ == "__main__":
    parsed = urlparse(AI_ENDPOINT if "://" in AI_ENDPOINT else f"http://{AI_ENDPOINT}")
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8100
    app.run(host=host, port=port, debug=False, use_reloader=False, threaded=True)
