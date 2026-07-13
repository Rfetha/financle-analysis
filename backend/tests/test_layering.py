"""Katman sınırı: model/agent dışındaki katmanlar provider kütüphanelerini görmez.

Spec: docs/superpowers/specs/2026-07-13-model-layer-and-mcp-door-design.md
Bu test olmadan "katmanlı mimari" laftan ibaret — provider ithali sessizce sızar.
"""

import re
from pathlib import Path

PROVIDER_FREE_DIRS = ["api", "tools", "domain", "store", "market"]
PROVIDER_LIBS = ("langchain", "langgraph", "openai", "anthropic", "claude_agent_sdk")

_IMPORT = re.compile(r"^\s*(?:from|import)\s+([\w.]+)", re.MULTILINE)


def _imports(path: Path) -> set[str]:
    return {m.group(1).split(".")[0] for m in _IMPORT.finditer(path.read_text(encoding="utf-8"))}


def test_core_layers_do_not_import_provider_libraries():
    root = Path(__file__).parent.parent / "sonar"
    leaks = {
        f"{path.relative_to(root)}: {lib}"
        for layer in PROVIDER_FREE_DIRS
        for path in (root / layer).rglob("*.py")
        for lib in _imports(path) & set(PROVIDER_LIBS)
    }
    assert not leaks, f"provider ithali çekirdek katmanlara sızmış: {sorted(leaks)}"
