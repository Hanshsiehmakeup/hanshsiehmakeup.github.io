#!/usr/bin/env python3
"""Rebuild the link-preview image and the meta tags in index.html.

The public site address lives only in preview.config.json. works.json stays
the list of posts (newest Instagram post first). Running this file twice in a
row leaves the tree unchanged.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "preview.config.json"
WORKS_PATH = ROOT / "works.json"
INDEX_PATH = ROOT / "index.html"
OG_DIR = ROOT / "og"

TARGET_WIDTH = 1200
MAX_BYTES = 1_000_000
START = "<!-- link-preview:start -->"
END = "<!-- link-preview:end -->"
TITLE = "HANS HSIEH \u2014 Makeup & Hair Artist"
DESCRIPTION = "Makeup & Hair Artist based in Taipei."
ALT = "Hans Hsieh makeup work"

OLD_TAGS = re.compile(
    r'<meta property="og:title" content="[^"]*">\n'
    r'<meta property="og:description" content="[^"]*">\n'
    r'<meta property="og:image" content="[^"]*">\n'
)


def site_url() -> str:
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"Missing {CONFIG_PATH.name}. It sets the public site URL.")
    url = str(data.get("siteUrl", "")).strip().rstrip("/")
    if not url.startswith("https://") or any(c in url for c in ' "\'<>'):
        raise SystemExit(
            'preview.config.json siteUrl must be an https address, '
            'for example "https://kuannauk.github.io/hanshsieh-studio".'
        )
    return url


def newest_photo() -> tuple[str, str, Path]:
    try:
        works = json.loads(WORKS_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit("Missing works.json.")
    posts = works.get("ig") or []
    if not posts:
        raise SystemExit("works.json has no Instagram posts in ig.")
    post = posts[0]
    images = post.get("i") or []
    if not images:
        raise SystemExit("The newest Instagram post has no images.")
    rel = images[0][0]
    code = str(post.get("code") or "post")
    safe = re.sub(r"[^A-Za-z0-9_-]", "", code) or "post"
    path = ROOT / rel
    if not path.is_file():
        raise SystemExit(f"Newest photo is missing on disk: {rel}")
    return safe, rel, path


def render_jpeg(source: Path) -> tuple[int, int, bytes]:
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image)
        if image.mode != "RGB":
            image = image.convert("RGB")
        width, height = image.size
        if width != TARGET_WIDTH:
            scaled_h = max(1, round(height * TARGET_WIDTH / width))
            image = image.resize((TARGET_WIDTH, scaled_h), Image.Resampling.LANCZOS)
        quality = 85
        data = b""
        while quality >= 50:
            buf = io.BytesIO()
            image.save(
                buf,
                format="JPEG",
                quality=quality,
                optimize=True,
                progressive=True,
                subsampling=2,
            )
            data = buf.getvalue()
            if len(data) <= MAX_BYTES:
                break
            quality -= 5
        if len(data) > MAX_BYTES:
            raise SystemExit(
                f"Preview JPEG is {len(data)} bytes, above the {MAX_BYTES} byte limit."
            )
        out_w, out_h = image.size
    if out_w != TARGET_WIDTH:
        raise SystemExit(f"Preview width is {out_w}, expected {TARGET_WIDTH}.")
    return out_w, out_h, data


def preview_block(page: str, image: str, width: int, height: int) -> str:
    return "\n".join(
        [
            START,
            "<!-- Regenerated from the newest works.json photo. Site URL: preview.config.json -->",
            '<meta property="og:type" content="website">',
            '<meta property="og:site_name" content="HANS HSIEH">',
            '<meta property="og:locale" content="zh_TW">',
            f'<meta property="og:url" content="{page}">',
            f'<meta property="og:title" content="{TITLE}">',
            f'<meta property="og:description" content="{DESCRIPTION}">',
            f'<meta property="og:image" content="{image}">',
            '<meta property="og:image:type" content="image/jpeg">',
            f'<meta property="og:image:width" content="{width}">',
            f'<meta property="og:image:height" content="{height}">',
            f'<meta property="og:image:alt" content="{ALT}">',
            '<meta name="twitter:card" content="summary_large_image">',
            f'<meta name="twitter:title" content="{TITLE}">',
            f'<meta name="twitter:description" content="{DESCRIPTION}">',
            f'<meta name="twitter:image" content="{image}">',
            f'<link rel="canonical" href="{page}">',
            END,
            "",
        ]
    )


def upsert_index(block: str) -> str:
    html = INDEX_PATH.read_text(encoding="utf-8")
    if START in html and END in html:
        pre, rest = html.split(START, 1)
        _, post = rest.split(END, 1)
        if post.startswith("\n"):
            post = post[1:]
        updated = pre + block + post
    else:
        updated, count = OLD_TAGS.subn(block, html, count=1)
        if count != 1:
            raise SystemExit(
                "index.html has no link-preview block and no og:title/og:image tags to replace."
            )
    if updated != html:
        INDEX_PATH.write_text(updated, encoding="utf-8")
    return updated


def write_image(name: str, data: bytes) -> Path:
    OG_DIR.mkdir(exist_ok=True)
    dest = OG_DIR / name
    for old in OG_DIR.iterdir():
        if old.is_file() and old != dest:
            old.unlink()
    if not dest.is_file() or dest.read_bytes() != data:
        dest.write_bytes(data)
    return dest


def main() -> None:
    base = site_url()
    code, rel, source = newest_photo()
    width, height, data = render_jpeg(source)
    digest = hashlib.sha256(data).hexdigest()[:8]
    name = f"{code}-{digest}.jpg"
    dest = write_image(name, data)
    page = base + "/"
    image = f"{base}/{dest.relative_to(ROOT).as_posix()}"
    html = upsert_index(preview_block(page, image, width, height))
    if f'property="og:image" content="{image}"' not in html:
        raise SystemExit("og:image was not written into index.html.")
    if f'name="twitter:image" content="{image}"' not in html:
        raise SystemExit("twitter:image was not written into index.html.")
    print(f"preview {image} {width}x{height} {len(data)}")


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        sys.exit(0)
