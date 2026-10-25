"""Presentation formatting for app notifications, never translation content."""
import re


def notification_text(value: str) -> str:
    text = str(value).translate(str.maketrans("", "", "。！!"))
    # Keep decimal points, filenames and domains while removing sentence stops.
    return re.sub(r"\.(?=\s|$)", "", text).strip()
