#!/usr/bin/env python3
"""
task_1_starter_code.py
Simple shelf-packing algorithm that:
 - loads images from input folder
 - crops transparent area (if present)
 - preserves aspect ratio
 - packs images into pages (A4 or Letter) using shelf algorithm
 - composes pages and saves as multi-page PDF (output.pdf)

Usage:
python task_1_starter_code.py --input input_images --output output.pdf --page A4 --dpi 300 --quality 85
"""
import os
import argparse
from PIL import Image, ImageOps

PAGE_SIZES_INCH = {
    "A4": (8.27, 11.69),
    "LETTER": (8.5, 11.0)
}

def list_images(folder):
    exts = (".png", ".jpg", ".jpeg", ".webp", ".tiff", ".bmp")
    return [os.path.join(folder, f) for f in sorted(os.listdir(folder)) if f.lower().endswith(exts)]

def crop_transparent(im: Image.Image) -> Image.Image:
    # If image has alpha, crop to alpha bbox. If not alpha, try to crop by bounding box of non-white.
    if im.mode in ("RGBA", "LA") or ("transparency" in im.info):
        # ensure RGBA
        rgba = im.convert("RGBA")
        bbox = rgba.getchannel("A").getbbox()
        if bbox:
            return rgba.crop(bbox).convert("RGBA")
        else:
            return rgba.convert("RGB")
    else:
        # no alpha: try to trim border by converting to RGB and getting bbox of non-background
        rgb = im.convert("RGB")
        bbox = rgb.getbbox()
        if bbox:
            return rgb.crop(bbox)
        else:
            return rgb

def open_and_preprocess(path):
    im = Image.open(path)
    im = crop_transparent(im)
    # Force RGBA if original had transparency, else RGB
    return im

def pack_images_shelf(images_sizes, page_w_px, page_h_px, padding=8):
    """
    images_sizes: list of tuples (w_px, h_px, original_index)
    Simple shelf packing:
      - place images left-to-right on a shelf
      - shelf height = max height of images in shelf
      - when no space, start new shelf (y moves down)
      - when no vertical space, create new page
    Returns: list of pages; each page is list of placements (index, x, y, w, h)
    """
    pages = []
    i = 0
    n = len(images_sizes)
    while i < n:
        placements = []
        y = padding
        while y < page_h_px - padding and i < n:
            shelf_x = padding
            shelf_height = 0
            # gather images that fit in this shelf until width used
            while i < n:
                w, h, idx = images_sizes[i]
                if w + shelf_x + padding <= page_w_px:
                    placements.append((idx, shelf_x, y, w, h))
                    shelf_x += w + padding
                    if h > shelf_height:
                        shelf_height = h
                    i += 1
                else:
                    # current image doesn't fit horizontally -> finish shelf
                    break
            if shelf_height == 0:
                # a single image is wider than page; we must scale it down to page width - 2*padding
                # reduce the current image width to fit
                w, h, idx = images_sizes[i]
                max_w = page_w_px - 2 * padding
                if max_w <= 0:
                    raise RuntimeError("Page width too small for packing")
                scale = max_w / w
                new_w = int(round(w * scale))
                new_h = int(round(h * scale))
                placements.append((idx, padding, y, new_w, new_h))
                i += 1
                shelf_height = new_h
            y += shelf_height + padding
            if y >= page_h_px - padding and i < n:
                # next shelf would overflow; page full
                break
        pages.append(placements)
    return pages

def compose_pages(pil_images, pages_placement, page_px):
    page_w_px, page_h_px = page_px
    composed = []
    for placements in pages_placement:
        page = Image.new("RGB", (page_w_px, page_h_px), (255,255,255))
        for idx, x, y, w, h in placements:
            im = pil_images[idx]
            # resize preserving aspect ratio to (w,h)
            resized = im.copy()
            # If it has alpha, paste onto white background first for PDF consistency
            if resized.mode in ("RGBA", "LA"):
                bg = Image.new("RGBA", resized.size, (255,255,255,255))
                bg.paste(resized, (0,0), resized)
                resized = bg.convert("RGB")
            else:
                resized = resized.convert("RGB")
            resized = resized.resize((w, h), Image.LANCZOS)
            page.paste(resized, (x, y))
        composed.append(page)
    return composed

def main(args):
    os.makedirs(args.input, exist_ok=True)
    images_paths = list_images(args.input)
    if not images_paths:
        print("No images found in", args.input)
        return

    # page size in pixels at chosen DPI
    page_inches = PAGE_SIZES_INCH.get(args.page.upper(), PAGE_SIZES_INCH["A4"])
    page_w_px = int(round(page_inches[0] * args.dpi))
    page_h_px = int(round(page_inches[1] * args.dpi))
    page_px = (page_w_px, page_h_px)

    print(f"Page {args.page} at {args.dpi} DPI -> {page_w_px} x {page_h_px} px")

    # open and preprocess
    pil_images = []
    for p in images_paths:
        im = open_and_preprocess(p)
        pil_images.append(im)

    # Determine sizes (option: scale down images that are larger than page dimensions)
    sizes = []
    for i, im in enumerate(pil_images):
        w, h = im.size
        # ensure images not bigger than page: scale down if either dimension exceeds page size minus padding
        max_w = page_w_px - 16
        max_h = page_h_px - 16
        scale = min(1.0, max_w / w if w>0 else 1.0, max_h / h if h>0 else 1.0)
        w2 = int(round(w * scale))
        h2 = int(round(h * scale))
        sizes.append((w2, h2, i))

    # Sort images by height descending (heuristic to improve packing)
    sizes.sort(key=lambda x: x[1], reverse=True)

    # pack into pages
    pages_placement = pack_images_shelf(sizes, page_w_px, page_h_px, padding=12)
    print(f"Packed into {len(pages_placement)} page(s).")

    # compose pages (PIL images)
    composed_pages = compose_pages(pil_images, pages_placement, page_px)

    # optional compression: save temporary JPEG per page or save directly to PDF
    # PIL's save with format="PDF" will embed images; we can control quality by saving to PDF via JPEG intermediate.
    out = args.output
    if out.lower().endswith(".pdf"):
        # convert pages to RGB and save as multi-page PDF
        pil_pages_for_pdf = [p.convert("RGB") for p in composed_pages]
        pil_pages_for_pdf[0].save(out, save_all=True, append_images=pil_pages_for_pdf[1:], resolution=args.dpi, quality=args.quality,
                                 optimize=True)
        print("Saved PDF:", out)
    else:
        # if user asked for directory of pages
        os.makedirs(out, exist_ok=True)
        for i, p in enumerate(composed_pages, start=1):
            fname = os.path.join(out, f"page_{i:03d}.jpg")
            p.save(fname, "JPEG", quality=args.quality, optimize=True)
        print("Saved pages to", out)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pack images into a PDF using a simple shelf algorithm.")
    parser.add_argument("--input", "-i", default="input_images", help="Input folder with images")
    parser.add_argument("--output", "-o", default="output.pdf", help="Output PDF file (or folder if not .pdf)")
    parser.add_argument("--page", "-p", default="A4", help="Page size: A4 or LETTER", choices=["A4", "LETTER"])
    parser.add_argument("--dpi", type=int, default=300, help="DPI for page rasterization (px per inch)")
    parser.add_argument("--quality", type=int, default=85, help="JPEG quality for compression (1-100)")
    args = parser.parse_args()
    main(args)
