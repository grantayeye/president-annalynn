#!/usr/bin/env python3
"""Render the five-second Annalynn campaign intro and its original sound sting."""

from __future__ import annotations

import math
import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


WIDTH, HEIGHT = 1280, 720
FPS, DURATION, SAMPLE_RATE = 30, 5.0, 48_000

CHARCOAL = "#242225"
PLUM = "#4d263e"
PLUM_LIGHT = "#673550"
CORAL = "#ef705d"
GOLD = "#d9ad55"
CREAM = "#fff8ed"

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / ".render-annalynn-intro"
FRAMES = BUILD / "frames"
WAV = BUILD / "campaign-sting.wav"
OUTPUT = Path(
    "/Users/grant/.codex/projects/codex-telegram-bridge/artifacts/"
    "annalynn-for-president-intro.mp4"
)

SERIF = "/System/Library/Fonts/Supplemental/Georgia.ttf"
SERIF_BOLD = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
SANS = "/System/Library/Fonts/Avenir Next.ttc"


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def ease_out_back(value: float) -> float:
    x = clamp(value) - 1.0
    c1 = 1.70158
    return 1.0 + (c1 + 1.0) * x**3 + c1 * x**2


def ease_out_cubic(value: float) -> float:
    return 1.0 - (1.0 - clamp(value)) ** 3


def ease_in_out(value: float) -> float:
    value = clamp(value)
    return 4 * value**3 if value < 0.5 else 1 - ((-2 * value + 2) ** 3) / 2


def fade_alpha(t: float) -> float:
    return clamp((t - 0.05) / 0.35) * clamp((DURATION - t) / 0.42)


def centered_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: str | tuple[int, int, int, int],
    *,
    stroke_width: int = 0,
    stroke_fill: str | None = None,
) -> None:
    box = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    width = box[2] - box[0]
    height = box[3] - box[1]
    draw.text(
        (xy[0] - width / 2, xy[1] - height / 2 - box[1]),
        text,
        font=font,
        fill=fill,
        stroke_width=stroke_width,
        stroke_fill=stroke_fill,
    )


def tracking_text(
    draw: ImageDraw.ImageDraw,
    center_x: float,
    y: float,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: str,
    tracking: float,
) -> None:
    widths = [draw.textlength(char, font=font) for char in text]
    total = sum(widths) + tracking * max(0, len(text) - 1)
    x = center_x - total / 2
    for char, width in zip(text, widths):
        draw.text((x, y), char, font=font, fill=fill)
        x += width + tracking


def draw_badge(layer: Image.Image, x: float, y: float, scale: float, alpha: int) -> None:
    badge = Image.new("RGBA", (180, 180), (0, 0, 0, 0))
    draw = ImageDraw.Draw(badge)
    draw.rounded_rectangle((14, 14, 166, 166), radius=39, fill=PLUM, outline=GOLD, width=3)
    font = ImageFont.truetype(SERIF_BOLD, 108)
    centered_text(draw, (90, 89), "A", font, CREAM)
    draw.line((38, 103, 58, 123, 100, 78), fill=CORAL, width=12, joint="curve")
    draw.ellipse((138, 23, 158, 43), fill=GOLD)
    badge_size = max(1, round(180 * scale))
    badge = badge.resize((badge_size, badge_size), Image.Resampling.LANCZOS)
    if alpha < 255:
        opacity = badge.getchannel("A").point(lambda p: p * alpha // 255)
        badge.putalpha(opacity)
    layer.alpha_composite(badge, (round(x - badge.width / 2), round(y - badge.height / 2)))


def render_frame(frame_number: int) -> Image.Image:
    t = frame_number / FPS
    overall = fade_alpha(t)
    image = Image.new("RGBA", (WIDTH, HEIGHT), CHARCOAL)
    draw = ImageDraw.Draw(image)

    # Branded editorial background: diagonal panels, hairlines, and orbit rings.
    wipe = ease_in_out(t / 0.72)
    plum_edge = -420 + wipe * 930
    draw.polygon([(0, 0), (plum_edge, 0), (plum_edge - 170, HEIGHT), (0, HEIGHT)], fill=PLUM)
    coral_edge = WIDTH + 290 - wipe * 410
    draw.polygon([(coral_edge, 0), (WIDTH, 0), (WIDTH, HEIGHT), (coral_edge - 150, HEIGHT)], fill=CORAL)
    gold_edge = WIDTH + 120 - wipe * 315
    draw.polygon([(gold_edge, 0), (gold_edge + 22, 0), (gold_edge - 130, HEIGHT), (gold_edge - 152, HEIGHT)], fill=GOLD)

    line_offset = int((t * 22) % 15)
    for y in range(38 + line_offset, HEIGHT, 15):
        draw.line((60, y, WIDTH - 60, y), fill=(255, 248, 237, 18), width=1)

    orbit_progress = ease_out_cubic((t - 0.2) / 0.9)
    orbit_box = (WIDTH // 2 - 296, HEIGHT // 2 - 296, WIDTH // 2 + 296, HEIGHT // 2 + 296)
    if orbit_progress > 0:
        draw.arc(orbit_box, -95, -95 + 330 * orbit_progress, fill=GOLD, width=2)
    orbit_box_2 = (WIDTH // 2 - 250, HEIGHT // 2 - 250, WIDTH // 2 + 250, HEIGHT // 2 + 250)
    if orbit_progress > 0:
        draw.arc(orbit_box_2, 85, 85 + 285 * orbit_progress, fill=PLUM_LIGHT, width=2)

    # Small campaign badge lands first.
    badge_progress = ease_out_back((t - 0.28) / 0.62)
    if badge_progress > 0:
        draw_badge(image, WIDTH / 2, 104, 0.34 * badge_progress, round(255 * clamp(badge_progress)))

    # Name reveal is clipped from left to right and eases upward.
    name_progress = ease_out_cubic((t - 0.68) / 0.72)
    if name_progress > 0:
        name_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        name_draw = ImageDraw.Draw(name_layer)
        name_font = ImageFont.truetype(SERIF_BOLD, 126)
        centered_text(name_draw, (WIDTH / 2, 267 + 28 * (1 - name_progress)), "ANNALYNN", name_font, CREAM)
        reveal = Image.new("L", (WIDTH, HEIGHT), 0)
        ImageDraw.Draw(reveal).rectangle((145, 170, 145 + 990 * name_progress, 350), fill=255)
        name_layer.putalpha(Image.composite(name_layer.getchannel("A"), Image.new("L", (WIDTH, HEIGHT), 0), reveal))
        image.alpha_composite(name_layer)

    # Coral office ribbon arrives with the second impact.
    ribbon_progress = ease_out_back((t - 1.38) / 0.62)
    if ribbon_progress > 0:
        ribbon = Image.new("RGBA", (720, 108), (0, 0, 0, 0))
        ribbon_draw = ImageDraw.Draw(ribbon)
        ribbon_draw.rounded_rectangle((8, 8, 712, 100), radius=18, fill=CORAL, outline=GOLD, width=4)
        office_font = ImageFont.truetype(SANS, 49)
        tracking_text(ribbon_draw, 360, 19, "FOR PRESIDENT", office_font, CREAM, 3.8)
        shadow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        ribbon_x = -460 + (WIDTH / 2 + 460) * ribbon_progress
        shadow_draw.rounded_rectangle((ribbon_x - 356, 342, ribbon_x + 356, 442), radius=20, fill=(0, 0, 0, 100))
        shadow = shadow.filter(ImageFilter.GaussianBlur(13))
        image.alpha_composite(shadow)
        image.alpha_composite(ribbon, (round(ribbon_x - 360), 329))

    # The exact slogan is the closing message and holds long enough to read.
    slogan_progress = ease_out_cubic((t - 2.30) / 0.60)
    if slogan_progress > 0:
        slogan_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        slogan_draw = ImageDraw.Draw(slogan_layer)
        slogan_font = ImageFont.truetype(SERIF, 54)
        alpha = round(255 * clamp(slogan_progress))
        centered_text(
            slogan_draw,
            (WIDTH / 2, 504 + 24 * (1 - slogan_progress)),
            "Your Ideas. Your Voice.",
            slogan_font,
            (255, 248, 237, alpha),
        )
        image.alpha_composite(slogan_layer)

    # Finishing sparkle accents echo the gold dot in the campaign mark.
    sparkle_progress = ease_out_cubic((t - 2.72) / 0.50)
    if sparkle_progress > 0:
        sparkle_points = [(325, 220), (963, 230), (256, 474), (1012, 492), (388, 560), (910, 560)]
        for index, (x, y) in enumerate(sparkle_points):
            pulse = clamp(math.sin((t * 5.5) + index * 0.9) * 0.35 + 0.65)
            radius = (3 + 6 * pulse) * sparkle_progress
            draw.line((x - radius, y, x + radius, y), fill=GOLD, width=2)
            draw.line((x, y - radius, x, y + radius), fill=GOLD, width=2)

    if overall < 1:
        black = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, round(255 * (1 - overall))))
        image.alpha_composite(black)
    return image.convert("RGB")


def add_tone(track: np.ndarray, start: float, duration: float, frequency: float, amplitude: float, pan: float = 0.0) -> None:
    first = round(start * SAMPLE_RATE)
    length = min(round(duration * SAMPLE_RATE), len(track) - first)
    if length <= 0:
        return
    time = np.arange(length) / SAMPLE_RATE
    attack = np.clip(time / 0.028, 0, 1)
    release = np.clip((duration - time) / 0.32, 0, 1)
    envelope = attack * release * np.exp(-0.34 * time)
    tone = (
        np.sin(2 * np.pi * frequency * time)
        + 0.24 * np.sin(2 * np.pi * frequency * 2 * time)
        + 0.08 * np.sin(2 * np.pi * frequency * 3 * time)
    ) * envelope * amplitude
    left_gain = math.sqrt((1 - pan) / 2)
    right_gain = math.sqrt((1 + pan) / 2)
    track[first : first + length, 0] += tone * left_gain
    track[first : first + length, 1] += tone * right_gain


def add_impact(track: np.ndarray, start: float, amplitude: float) -> None:
    rng = np.random.default_rng(round(start * 10_000) + 17)
    first = round(start * SAMPLE_RATE)
    duration = 0.58
    length = min(round(duration * SAMPLE_RATE), len(track) - first)
    time = np.arange(length) / SAMPLE_RATE
    low = np.sin(2 * np.pi * (78 * time - 22 * time**2)) * np.exp(-8.2 * time)
    click = rng.normal(0, 1, length)
    click = np.convolve(click, np.ones(12) / 12, mode="same") * np.exp(-34 * time)
    impact = amplitude * (0.78 * low + 0.36 * click)
    track[first : first + length, 0] += impact
    track[first : first + length, 1] += impact


def create_audio() -> None:
    samples = round(DURATION * SAMPLE_RATE)
    track = np.zeros((samples, 2), dtype=np.float64)
    rng = np.random.default_rng(20260818)

    # Short stereo whoosh into the logo landing.
    whoosh_length = round(0.82 * SAMPLE_RATE)
    noise = rng.normal(0, 1, whoosh_length)
    smooth = np.convolve(noise, np.ones(20) / 20, mode="same")
    whoosh_time = np.arange(whoosh_length) / SAMPLE_RATE
    whoosh_env = np.sin(np.pi * np.clip(whoosh_time / 0.82, 0, 1)) ** 1.7
    whoosh = smooth * whoosh_env * 0.24
    track[:whoosh_length, 0] += whoosh * np.linspace(1.0, 0.35, whoosh_length)
    track[:whoosh_length, 1] += whoosh * np.linspace(0.35, 1.0, whoosh_length)

    add_impact(track, 0.58, 0.52)
    add_impact(track, 1.52, 0.68)
    add_impact(track, 2.46, 0.36)

    # Warm, optimistic original campaign chord.
    for frequency, pan in [(261.63, -0.45), (329.63, 0.15), (392.00, 0.45), (523.25, -0.05)]:
        add_tone(track, 1.52, 3.10, frequency, 0.115, pan)
    add_tone(track, 2.45, 2.05, 659.25, 0.095, 0.35)
    add_tone(track, 2.72, 1.74, 783.99, 0.070, -0.28)
    add_tone(track, 2.94, 1.45, 1046.50, 0.055, 0.46)

    # Two light gold-dot chimes on the final slogan.
    for start, frequency, pan in [(2.82, 1318.51, -0.42), (3.12, 1567.98, 0.42)]:
        add_tone(track, start, 0.78, frequency, 0.048, pan)

    fade_out = np.ones(samples)
    fade_start = round(4.48 * SAMPLE_RATE)
    fade_out[fade_start:] = np.linspace(1, 0, samples - fade_start)
    track *= fade_out[:, None]
    peak = np.max(np.abs(track))
    if peak:
        track *= 0.91 / peak
    pcm = np.int16(np.clip(track, -1, 1) * 32767)
    with wave.open(str(WAV), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes(pcm.tobytes())


def main() -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise SystemExit("ffmpeg is required")
    FRAMES.mkdir(parents=True, exist_ok=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    for frame_number in range(round(FPS * DURATION)):
        render_frame(frame_number).save(FRAMES / f"frame-{frame_number:04d}.png", optimize=True)
    create_audio()
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-framerate",
            str(FPS),
            "-i",
            str(FRAMES / "frame-%04d.png"),
            "-i",
            str(WAV),
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-crf",
            "17",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            "-t",
            f"{DURATION:.1f}",
            str(OUTPUT),
        ],
        check=True,
    )
    print(OUTPUT)


if __name__ == "__main__":
    main()
