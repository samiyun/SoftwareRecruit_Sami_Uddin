"""
sender.py — pushes randomly selected images to the web app over WebSocket.

This is the "Python script" required by the task: it sends image data to the
application via WebSocket (not HTTP).

Usage:
    python sender.py                         # random image every 2s from data/samples
    python sender.py --folder ../Socket      # quick test: sends Utah.bmp
    python sender.py --count 5 --delay 0.5   # send 5 images quickly
    python sender.py --folder C:/path/images # any folder of images
"""

from __future__ import annotations

import argparse
import asyncio
import pathlib
import random

import websockets

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}


def find_images(folder: pathlib.Path) -> list[pathlib.Path]:
    return [
        p
        for p in folder.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    ]


async def run(args: argparse.Namespace) -> None:
    folder = pathlib.Path(args.folder).resolve()
    images = find_images(folder)

    if not images:
        print(f"No images found in '{folder}'.")
        print("Drop some .jpg/.png/.bmp files into data/samples first,")
        print("or point --folder at a folder that has images.")
        return

    print(f"Sending from '{folder}' ({len(images)} images) -> {args.url}")

    sent = 0
    while True:
        path = random.choice(images)
        data = path.read_bytes()
        try:
            async with websockets.connect(args.url, max_size=None) as ws:
                await ws.send(data)
            print(f"sent {path.name} ({len(data):,} bytes)")
        except (OSError, websockets.exceptions.WebSocketException) as exc:
            print(f"connection failed ({exc}); retrying in 2s…")
            await asyncio.sleep(2)
            continue

        sent += 1
        if args.count and sent >= args.count:
            break
        await asyncio.sleep(args.delay)


def main() -> None:
    parser = argparse.ArgumentParser(description="Stream random images to the TMR UI backend.")
    parser.add_argument("--url", default="ws://127.0.0.1:8000/ws")
    parser.add_argument("--folder", default="data/samples")
    parser.add_argument("--delay", type=float, default=2.0, help="seconds between images")
    parser.add_argument("--count", type=int, default=0, help="stop after N images (0 = forever)")
    args = parser.parse_args()

    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
