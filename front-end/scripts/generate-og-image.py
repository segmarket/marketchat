#!/usr/bin/env python3
"""Gera PNG 1200x630 para preview WhatsApp/Facebook (marca branca, sem recorte)."""
from pathlib import Path

from PIL import Image

BRAND_DIR = Path(__file__).resolve().parents[1] / "public" / "images" / "brand"
MASCOTE = BRAND_DIR / "logotipo_marketchat_mascote_BRANCO.gif"
NOME = BRAND_DIR / "logotipo_marketchat_nome_BRANCO.gif"
COMPLETO = BRAND_DIR / "logotipo_marketchat_completo_BRANCO.gif"
OUTPUT = BRAND_DIR / "og-marketchat-share.png"
SIZE = (1200, 630)
BG = (15, 23, 42, 255)
GAP = 32


def _trim_logo(logo: Image.Image) -> Image.Image:
    rgba = logo.convert("RGBA")
    alpha = rgba.split()[3]
    mask = alpha.point(lambda a: 255 if a > 32 else 0)
    bbox = mask.getbbox()
    return rgba.crop(bbox) if bbox else rgba


def _load(path: Path) -> Image.Image:
    im = Image.open(path)
    if getattr(im, "n_frames", 1) > 1:
        im.seek(0)
    return _trim_logo(im)


def _resize_height(logo: Image.Image, height: int) -> Image.Image:
    ratio = height / logo.height
    nw = max(1, int(logo.width * ratio))
    return logo.resize((nw, height), Image.Resampling.LANCZOS)


def _fit_inside(logo: Image.Image, max_w: int, max_h: int) -> Image.Image:
    ratio = min(max_w / logo.width, max_h / logo.height)
    nw, nh = max(1, int(logo.width * ratio)), max(1, int(logo.height * ratio))
    return logo.resize((nw, nh), Image.Resampling.LANCZOS)


def _compose_lockup(max_w: int, max_h: int) -> tuple[Image.Image, str]:
    mascote = _load(MASCOTE)
    nome = _load(NOME)

    # Mascote ocupa ~42% da altura do card; nome encaixa na largura restante.
    m_h = min(int(SIZE[1] * 0.42), max_h)
    m = _resize_height(mascote, m_h)
    nome_max_w = max_w - m.width - GAP
    nome_max_h = min(m_h, max_h)
    n = _fit_inside(nome, nome_max_w, nome_max_h)

    row_w = m.width + GAP + n.width
    row_h = max(m.height, n.height)
    row = Image.new("RGBA", (row_w, row_h), (0, 0, 0, 0))
    row.paste(m, (0, (row_h - m.height) // 2), m)
    row.paste(n, (m.width + GAP, (row_h - n.height) // 2), n)
    return row, f"lockup {row_w}x{row_h}"


def main() -> None:
    canvas = Image.new("RGBA", SIZE, BG)
    pad_x, pad_y = 56, 48
    max_w = SIZE[0] - 2 * pad_x
    max_h = SIZE[1] - 2 * pad_y

    if MASCOTE.exists() and NOME.exists():
        art, label = _compose_lockup(max_w, max_h)
    else:
        art = _fit_inside(_load(COMPLETO), max_w, int(max_h * 0.5))
        label = f"completo {art.width}x{art.height}"

    x = (SIZE[0] - art.width) // 2
    y = (SIZE[1] - art.height) // 2
    canvas.paste(art, (x, y), art)

    canvas.convert("RGB").save(OUTPUT, "PNG", optimize=True)
    legacy = BRAND_DIR / "og-marketchat.png"
    canvas.convert("RGB").save(legacy, "PNG", optimize=True)
    print(f"OK: {OUTPUT} ({label} em {SIZE[0]}x{SIZE[1]})")


if __name__ == "__main__":
    main()
