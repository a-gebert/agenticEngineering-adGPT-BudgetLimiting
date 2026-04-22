#!/usr/bin/env python3
"""
CSharpier Check Hook for Claude Code

Triggers after every C# file edit (Edit / Write / MultiEdit).
Runs `dotnet csharpier check` on the changed file and reports
formatting violations back to Claude so it can fix them.
"""

import json
import subprocess
import sys


def main():
    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})
    tool_response = input_data.get("tool_response", {})

    if tool_name not in ("Edit", "Write", "MultiEdit"):
        sys.exit(0)

    file_path = tool_response.get("filePath") or tool_input.get("file_path", "")

    if not file_path.endswith(".cs"):
        sys.exit(0)

    try:
        result = subprocess.run(
            ["dotnet", "csharpier", "check", file_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        sys.exit(0)

    if result.returncode != 0:
        output = json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": (
                        f"CSharpier formatting violation in {file_path}.\n"
                        f"{result.stdout}\n{result.stderr}\n"
                        "Run `dotnet csharpier format <file>` to fix, "
                        "or apply the formatting changes manually."
                    ),
                }
            }
        )
        print(output)


if __name__ == "__main__":
    main()
