"""Regex-based firmware validation email parser."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class FirmwareInfo:
    """Parsed firmware validation data from an email."""

    device: str
    type: str
    version: str
    patch: str
    md5: str
    status: str = "active"


# Subject: [TEST MODEL] SW Validation
_SUBJECT_DEVICE_RE = re.compile(r"\[([^\]]+)\]", re.IGNORECASE)

# -SW Version : Logicom_VISION_MAX_TEST_HW01_SW03
_SW_VERSION_RE = re.compile(
    r"-\s*SW\s+Version\s*:\s*(.+)",
    re.IGNORECASE,
)

# -Patch version : 05-02-2026
_PATCH_VERSION_RE = re.compile(
    r"-\s*Patch\s+version\s*:\s*(.+)",
    re.IGNORECASE,
)

# -MD5 value : 906C0D61870FF00ECFCDA7D719571B8F
_MD5_RE = re.compile(
    r"-\s*MD5\s+value\s*:\s*([A-Fa-f0-9]+)",
    re.IGNORECASE,
)


def _detect_type(body: str) -> str:
    """
    Determine device type from email body content.

    Rules:
    - smartphone  -> Phone
    - TAB or Tablet -> Tablet
    - otherwise or no special keyword -> Others
    """
    body_lower = body.lower()
    if re.search(r"\btab\b", body_lower) or "tablet" in body_lower:
        return "Tablet"
    if "smartphone" in body_lower:
        return "Phone"
    # Default when nothing special is mentioned
    return "Others"


def _extract_device_from_subject(subject: str) -> Optional[str]:
    """Extract device name from subject bracket notation [DEVICE]."""
    match = _SUBJECT_DEVICE_RE.search(subject)
    if match:
        return match.group(1).strip()
    return None


# Body fallback: "... validated the NEW soft version of TAB FOLD 12,"
_BODY_DEVICE_RE = re.compile(
    r"soft\s+version\s+of\s+(?:smartphone\s+)?([^,\n]+)",
    re.IGNORECASE,
)


def _extract_device_from_body(body: str) -> Optional[str]:
    """Extract device name from email body when subject has no [DEVICE]."""
    match = _BODY_DEVICE_RE.search(body)
    if match:
        return match.group(1).strip()
    return None


def parse_firmware_email(subject: str, body: str) -> Optional[FirmwareInfo]:
    """
    Parse a firmware validation email and extract structured data.

    Args:
        subject: Email subject line.
        body: Email body text (plain text).

    Returns:
        FirmwareInfo if all required fields are found, otherwise None.
    """

    device = _extract_device_from_subject(subject)
    if not device:
        device = _extract_device_from_body(body)
    if not device:
        return None

    version_match = _SW_VERSION_RE.search(body)
    patch_match = _PATCH_VERSION_RE.search(body)
    md5_match = _MD5_RE.search(body)

    if not version_match:
        return None

    if not patch_match:
        print("Patch version not found")

    if not md5_match:
        print("MD5 not found")

    version = version_match.group(1).strip()

    patch = (
        patch_match.group(1).strip()
        if patch_match
        else ""
    )

    md5 = (
        md5_match.group(1).strip()
        if md5_match
        else ""
    )

    device_type = _detect_type(body)

    return FirmwareInfo(
        device=device,
        type=device_type,
        version=version,
        patch=patch,
        md5=md5,
        status="active",
    )


_SAMPLE_SUBJECT = "[TEST MODEL] SW Validation"
_SAMPLE_BODY = """After the check, we have validated the new soft version of smartphone TEST MODEL,

SW is OK for MP :

-SW file : Balei-A537-A16-v1.0h-Logicom_VISION_MAX_TEST_user_20260605.img

-SW Version : Logicom_VISION_MAX_TEST_HW01_SW03

-Patch version : 05-02-2026

-MD5 value : 906C0D61870FF00ECFCDA7D719571B8F
"""


if __name__ == "__main__":
    """Run parser self-test with built-in sample email."""
    import argparse

    parser = argparse.ArgumentParser(description="Firmware email parser test tool")
    parser.add_argument("--subject", default=_SAMPLE_SUBJECT, help="Email subject")
    parser.add_argument("--body", default=_SAMPLE_BODY, help="Email body text")
    args = parser.parse_args()

    print("Parser Test Tool")
    print(f"  Subject: {args.subject}")
    print("-" * 50)

    result = parse_firmware_email(args.subject, args.body)
    if result is None:
        print("Parse failed: could not extract all required fields.")
    else:
        print(f"  device  : {result.device}")
        print(f"  type    : {result.type}")
        print(f"  version : {result.version}")
        print(f"  patch   : {result.patch}")
        print(f"  md5     : {result.md5}")
        print(f"  status  : {result.status}")

    print("-" * 50)
    print("Tip: python parser.py --subject \"[MODEL] SW Validation\" --body \"...\"")
