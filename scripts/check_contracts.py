"""Run the unmodified linter rules with the cached pinned SDK, offline.

genvm-lint 0.10.0 otherwise requests GitHub's latest tag even when the contract
pins a runner already present in its cache. Only artifact selection is replaced;
lint, schema validation, imports and the exact runner manifest remain checked.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    mode = "typecheck" if "--typecheck" in sys.argv else "check"
    cache = Path.home() / ".cache" / "genvm-linter" / "genvm-universal-v0.3.0-rc6.tar.xz"
    if not cache.exists():
        raise RuntimeError("Pinned SDK cache missing; run genvm-lint download --version v0.3.0-rc6")
    report = []
    for file in sorted((ROOT / "contracts").glob("*.py")):
        code = (
            "from pathlib import Path; "
            "import genvm_linter.validate.sdk_loader as sdk; "
            "sdk.download_artifacts=lambda progress_callback=None:Path(" + repr(str(cache)) + "); "
            "import genvm_linter.cli as cli; "
            "cli.download_artifacts=lambda *a,**k:Path(" + repr(str(cache)) + "); "
            "from genvm_linter.cli import main; "
            "main([" + repr(mode) + "," + repr(str(file)) + ",'--json'])")
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        print(file.name + ": " + result.stdout.strip(), flush=True)
        if result.returncode:
            raise RuntimeError(result.stderr or result.stdout)
        report.append({"source": file.name, "result": json.loads(result.stdout)})
    (ROOT / ("typecheck-results.json" if mode == "typecheck" else "lint-results.json")).write_text(json.dumps({"sdk": "v0.3.0-rc6",
        "runner": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6",
        "artifact_selection": "cached release, offline", "contracts": report}, indent=2) + "\n")


if __name__ == "__main__":
    main()
