#!/usr/bin/env python3
"""
Preset Management Script
List and apply council presets.

Usage:
    python execution/manage_presets.py --action list
    python execution/manage_presets.py --action apply --preset code_review
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import httpx
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx"])
    import httpx

BASE_URL = "http://localhost:8001"


async def list_presets() -> dict:
    """List all available presets."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/presets")
        response.raise_for_status()
        return response.json()


async def apply_preset(preset_id: str) -> dict:
    """Apply a preset configuration."""
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/api/presets/{preset_id}/apply")
        response.raise_for_status()
        return response.json()


async def get_config() -> dict:
    """Get current configuration."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/config")
        response.raise_for_status()
        return response.json()


def format_presets(presets: dict) -> str:
    """Format presets for display."""
    output = []
    output.append("=" * 60)
    output.append("AVAILABLE COUNCIL PRESETS")
    output.append("=" * 60)

    for preset in presets.get("presets", []):
        output.append(f"\n📋 {preset['id'].upper()}")
        output.append(f"   Name: {preset['name']}")
        output.append(f"   Description: {preset['description']}")
        output.append(f"   Chairman: {preset['chairman']}")
        output.append(f"   Council: {len(preset['models'])} models")
        for model in preset['models'][:3]:
            output.append(f"     - {model}")
        if len(preset['models']) > 3:
            output.append(f"     ... and {len(preset['models']) - 3} more")

    output.append("\n" + "=" * 60)
    output.append("Usage: python manage_presets.py --action apply --preset <id>")

    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description="Manage council presets")
    parser.add_argument("--action", "-a", required=True,
                       choices=["list", "apply", "current"],
                       help="Action to perform")
    parser.add_argument("--preset", "-p", help="Preset ID (for apply action)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    try:
        if args.action == "list":
            result = asyncio.run(list_presets())
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(format_presets(result))

        elif args.action == "apply":
            if not args.preset:
                print("ERROR: --preset required for apply action")
                sys.exit(1)
            result = asyncio.run(apply_preset(args.preset))
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"✅ Applied preset: {result['preset_name']}")
                print(f"   Chairman: {result['chairman_model']}")
                print(f"   Council: {', '.join(result['council_models'])}")

        elif args.action == "current":
            result = asyncio.run(get_config())
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print("Current Configuration:")
                print(f"  Chairman: {result.get('chairman_model', 'N/A')}")
                print(f"  Council: {', '.join(result.get('council_models', []))}")

    except httpx.ConnectError:
        print("ERROR: Cannot connect to backend. Is the server running on port 8001?")
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            print(f"ERROR: Preset '{args.preset}' not found")
        else:
            print(f"ERROR: HTTP {e.response.status_code}: {e.response.text}")
        sys.exit(1)


if __name__ == "__main__":
    main()
