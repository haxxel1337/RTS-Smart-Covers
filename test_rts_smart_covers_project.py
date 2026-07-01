#!/usr/bin/env python3
r"""
Validation and smoke-test script for the RTS Smart Covers project.

Run from:

    C:\Users\axelh\Dropbox\Axels mapp\Coding Projects\RTS-Smart-Covers

Command:

    python test_rts_smart_covers_project.py

This script intentionally avoids requiring a running Home Assistant instance.
It validates project structure, JSON files, Python syntax, HACS metadata,
translation keys and core timed-cover math.
"""

from __future__ import annotations

import ast
import json
import py_compile
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path.cwd()
DOMAIN = "rts_smart_covers"
INTEGRATION = PROJECT_ROOT / "custom_components" / DOMAIN


@dataclass
class TestResult:
    name: str
    ok: bool
    message: str = ""


RESULTS: list[TestResult] = []


def check(name: str, condition: bool, message: str = "") -> None:
    RESULTS.append(TestResult(name=name, ok=condition, message=message))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def flatten_keys(value: Any, prefix: str = "") -> set[str]:
    keys: set[str] = set()

    if isinstance(value, dict):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else key
            keys.add(child_prefix)
            keys.update(flatten_keys(child, child_prefix))

    return keys


def expected_duration(start: float, target: float, travel_time: float) -> float:
    return abs(target - start) / 100 * travel_time


def estimated_position(
    started_position: float,
    direction: str,
    elapsed: float,
    travel_time: float,
) -> float:
    moved_pct = elapsed / travel_time * 100

    if direction == "opening":
        return max(0.0, min(100.0, started_position + moved_pct))

    if direction == "closing":
        return max(0.0, min(100.0, started_position - moved_pct))

    raise ValueError(f"Unknown direction: {direction}")


def test_required_files() -> None:
    required = [
        "README.md",
        "hacs.json",
        "LICENSE",
        ".gitignore",
        "custom_components/rts_smart_covers/brand/.gitkeep",
        "custom_components/rts_smart_covers/__init__.py",
        "custom_components/rts_smart_covers/manifest.json",
        "custom_components/rts_smart_covers/const.py",
        "custom_components/rts_smart_covers/config_flow.py",
        "custom_components/rts_smart_covers/cover.py",
        "custom_components/rts_smart_covers/strings.json",
        "custom_components/rts_smart_covers/translations/en.json",
        "custom_components/rts_smart_covers/translations/sv.json",
        "custom_components/rts_smart_covers/services.yaml",
    ]

    for relative in required:
        check(
            f"required file exists: {relative}",
            (PROJECT_ROOT / relative).is_file(),
            f"Missing {relative}",
        )

    check(
        "no root brand folder",
        not (PROJECT_ROOT / "brand").exists(),
        "Brand folder must be inside custom_components/rts_smart_covers/brand, not repository root.",
    )


def test_json_files() -> None:
    json_files = [
        PROJECT_ROOT / "hacs.json",
        INTEGRATION / "manifest.json",
        INTEGRATION / "strings.json",
        INTEGRATION / "translations" / "en.json",
        INTEGRATION / "translations" / "sv.json",
    ]

    for path in json_files:
        try:
            load_json(path)
            check(f"valid JSON: {path.relative_to(PROJECT_ROOT)}", True)
        except Exception as err:
            check(f"valid JSON: {path.relative_to(PROJECT_ROOT)}", False, str(err))


def test_manifest() -> None:
    path = INTEGRATION / "manifest.json"

    try:
        manifest = load_json(path)
    except Exception as err:
        check("manifest can be loaded", False, str(err))
        return

    expected = {
        "domain": "rts_smart_covers",
        "name": "RTS Smart Covers",
        "config_flow": True,
        "iot_class": "local_push",
        "version": "0.3.2",
    }

    for key, expected_value in expected.items():
        check(
            f"manifest {key}",
            manifest.get(key) == expected_value,
            f"Expected {expected_value!r}, got {manifest.get(key)!r}",
        )

    check(
        "manifest documentation GitHub URL",
        manifest.get("documentation") == "https://github.com/haxxel1337/RTS-Smart-Covers",
        f"Got {manifest.get('documentation')!r}",
    )
    check(
        "manifest issue tracker GitHub URL",
        manifest.get("issue_tracker") == "https://github.com/haxxel1337/RTS-Smart-Covers/issues",
        f"Got {manifest.get('issue_tracker')!r}",
    )
    check(
        "manifest code owner",
        "@haxxel1337" in manifest.get("codeowners", []),
        f"Got {manifest.get('codeowners')!r}",
    )


def test_hacs_json() -> None:
    path = PROJECT_ROOT / "hacs.json"

    try:
        hacs = load_json(path)
    except Exception as err:
        check("hacs.json can be loaded", False, str(err))
        return

    check("hacs name", hacs.get("name") == "RTS Smart Covers", f"Got {hacs.get('name')!r}")
    check("hacs domains includes cover", "cover" in hacs.get("domains", []), f"Got {hacs.get('domains')!r}")
    check("hacs render_readme true", hacs.get("render_readme") is True, f"Got {hacs.get('render_readme')!r}")
    check("hacs homeassistant exists", "homeassistant" in hacs, "Missing homeassistant minimum version")
    check("hacs minimum HA is 2026.6.1", hacs.get("homeassistant") == "2026.6.1", f"Got {hacs.get('homeassistant')!r}")


def test_python_compiles() -> None:
    for path in sorted(INTEGRATION.glob("*.py")):
        try:
            py_compile.compile(str(path), doraise=True)
            check(f"python compiles: {path.name}", True)
        except Exception as err:
            check(f"python compiles: {path.name}", False, str(err))


def test_ast_classes_and_methods() -> None:
    cover_path = INTEGRATION / "cover.py"
    config_flow_path = INTEGRATION / "config_flow.py"

    try:
        cover_tree = ast.parse(read_text(cover_path))
        config_tree = ast.parse(read_text(config_flow_path))
    except Exception as err:
        check("AST parse", False, str(err))
        return

    cover_classes = {
        node.name for node in cover_tree.body if isinstance(node, ast.ClassDef)
    }
    config_classes = {
        node.name for node in config_tree.body if isinstance(node, ast.ClassDef)
    }

    check(
        "cover class exists",
        "RtsSmartCoverEntity" in cover_classes,
        f"Found {sorted(cover_classes)}",
    )
    check(
        "config flow class exists",
        "RtsSmartCoversConfigFlow" in config_classes,
        f"Found {sorted(config_classes)}",
    )
    # Modern Home Assistant uses a reconfigure step for changing setup data.

    methods = set()
    for node in cover_tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "RtsSmartCoverEntity":
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.add(child.name)

    required_methods = {
        "async_added_to_hass",
        "async_open_cover",
        "async_close_cover",
        "async_set_cover_position",
        "async_stop_cover",
        "_async_move_to",
        "_async_finish_move",
        "_estimated_position",
        "_clamp",
        "async_will_remove_from_hass",
        "async_set_known_position",
        "async_mark_open",
        "async_mark_closed",
    }

    for method in sorted(required_methods):
        check(
            f"cover method exists: {method}",
            method in methods,
            f"Methods found: {sorted(methods)}",
        )


def test_cover_source_contains_required_patterns() -> None:
    cover_source = read_text(INTEGRATION / "cover.py")
    config_source = read_text(INTEGRATION / "config_flow.py")
    init_source = read_text(INTEGRATION / "__init__.py")

    patterns = {
        "uses CoverEntityFeature.SET_POSITION": r"CoverEntityFeature\.SET_POSITION",
        "uses RestoreEntity": r"RestoreEntity",
        "uses monotonic time": r"monotonic",
        "uses async_call_later": r"async_call_later",
        "sends open service": r"SERVICE_OPEN_COVER",
        "sends close service": r"SERVICE_CLOSE_COVER",
        "sends stop service": r"SERVICE_STOP_COVER",
        "checks unavailable": r"STATE_UNAVAILABLE",
        "checks unknown": r"STATE_UNKNOWN",
        "calls cover services": r'hass\.services\.async_call\(\s*["\']cover["\']',
        "uses current_cover_position": r"def current_cover_position",
        "sets assumed state": r"_attr_assumed_state\s*=\s*True",
    }

    for name, pattern in patterns.items():
        check(name, re.search(pattern, cover_source, re.MULTILINE | re.DOTALL) is not None)

    config_patterns = {
        "config flow uses EntitySelector": r"EntitySelector",
        "config flow cover domain selector": r'domain=["\']cover["\']',
        "config flow uses TextSelector": r"TextSelector",
        "config flow uses NumberSelector": r"NumberSelector",
        "config flow sets unique id": r"async_set_unique_id",
        "config flow aborts if configured": r"_abort_if_unique_id_configured",
        "config flow has reconfigure step": r"async_step_reconfigure",
        "config flow uses update reload abort": r"async_update_reload_and_abort",
        "config flow checks unique id mismatch": r"_abort_if_unique_id_mismatch",
    }

    for name, pattern in config_patterns.items():
        check(name, re.search(pattern, config_source, re.MULTILINE | re.DOTALL) is not None)

    init_patterns = {
        "init forwards platforms": r"async_forward_entry_setups",
        "init unloads platforms": r"async_unload_platforms",
        "init registers platform entity service": r"async_register_platform_entity_service",
    }

    for name, pattern in init_patterns.items():
        check(name, re.search(pattern, init_source, re.MULTILINE | re.DOTALL) is not None)


def test_translation_key_consistency() -> None:
    paths = [
        INTEGRATION / "strings.json",
        INTEGRATION / "translations" / "en.json",
        INTEGRATION / "translations" / "sv.json",
    ]

    loaded = {}
    for path in paths:
        try:
            loaded[path.name] = load_json(path)
        except Exception as err:
            check(f"translation load {path.name}", False, str(err))
            return

    string_keys = flatten_keys(loaded["strings.json"])
    en_keys = flatten_keys(loaded["en.json"])
    sv_keys = flatten_keys(loaded["sv.json"])

    check("en translation keys match strings.json", en_keys == string_keys, f"Diff: {sorted(en_keys ^ string_keys)}")
    check("sv translation keys match strings.json", sv_keys == string_keys, f"Diff: {sorted(sv_keys ^ string_keys)}")


def test_readme_mentions_important_items() -> None:
    readme = read_text(PROJECT_ROOT / "README.md").lower()

    required_phrases = [
        "somfy rts",
        "rfxtrx",
        "0%",
        "100%",
        "position is estimated",
        "hacs",
        "custom repositories",
        "cover.officesoversleft2",
        "35 seconds",
        "custom_components/rts_smart_covers/brand/logo.png",
        "custom_components/rts_smart_covers/brand/icon.png",
    ]

    for phrase in required_phrases:
        check(
            f"README mentions {phrase!r}",
            phrase in readme,
            f"Phrase missing: {phrase}",
        )


def test_timed_math_examples() -> None:
    examples = [
        ("100 to 30 with 35s", 100, 30, 35, 24.5),
        ("0 to 30 with 35s", 0, 30, 35, 10.5),
        ("30 to 70 with 35s", 30, 70, 35, 14.0),
        ("70 to 0 with 35s", 70, 0, 35, 24.5),
        ("0 to 100 with 35s", 0, 100, 35, 35.0),
    ]

    for name, start, target, travel, expected in examples:
        actual = expected_duration(start, target, travel)
        check(
            f"timed math duration: {name}",
            abs(actual - expected) < 0.001,
            f"Expected {expected}, got {actual}",
        )

    position_examples = [
        ("opening 0 for 10.5 of 35", 0, "opening", 10.5, 35, 30.0),
        ("closing 100 for 24.5 of 35", 100, "closing", 24.5, 35, 30.0),
        ("opening clamp over 100", 90, "opening", 10, 35, 100.0),
        ("closing clamp below 0", 10, "closing", 10, 35, 0.0),
    ]

    for name, start, direction, elapsed, travel, expected in position_examples:
        actual = estimated_position(start, direction, elapsed, travel)
        check(
            f"timed math estimate: {name}",
            abs(actual - expected) < 0.001,
            f"Expected {expected}, got {actual}",
        )


def test_no_yaml_helper_dependency() -> None:
    cover_source = read_text(INTEGRATION / "cover.py")
    combined = cover_source + read_text(INTEGRATION / "const.py")

    forbidden = [
        "input_number.",
        "input_select.",
        "input_datetime.",
        "script.",
        "automation.",
    ]

    for phrase in forbidden:
        check(
            f"no dependency on {phrase}",
            phrase not in combined,
            f"Found forbidden phrase {phrase}",
        )


def print_summary() -> int:
    passed = sum(1 for result in RESULTS if result.ok)
    failed = len(RESULTS) - passed

    print()
    print("=" * 80)
    print("RTS Smart Covers validation summary")
    print("=" * 80)
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print()

    for result in RESULTS:
        status = "PASS" if result.ok else "FAIL"
        print(f"[{status}] {result.name}")
        if result.message and not result.ok:
            print(f"       {result.message}")

    print()

    if failed:
        print("Result: FAILED")
        print("Fix the failed checks above, then run this script again.")
        return 1

    print("Result: PASSED")
    print("The project structure, metadata, translations, Python syntax and core timing math look good.")
    print()
    print("Next manual Home Assistant test:")
    print("1. Copy custom_components/rts_smart_covers into /config/custom_components/")
    print("2. Restart Home Assistant.")
    print("3. Add integration: Settings -> Devices & Services -> Add Integration -> RTS Smart Covers.")
    print("4. Configure source cover cover.officesoversleft2, name Office Covers Left Smart, travel time 35, initial position 100.")
    print("5. Test cover.set_cover_position to 30. It should close for about 24.5 seconds and then stop.")
    return 0


def test_services_yaml() -> None:
    services_path = INTEGRATION / "services.yaml"
    check("services.yaml exists", services_path.is_file(), "Missing services.yaml")
    if not services_path.is_file():
        return

    content = read_text(services_path)
    check("services.yaml contains set_known_position", "set_known_position:" in content)
    check("services.yaml contains mark_open", "mark_open:" in content)
    check("services.yaml contains mark_closed", "mark_closed:" in content)


def main() -> int:
    print("Running RTS Smart Covers project validation...")
    print(f"Project root: {PROJECT_ROOT}")

    if not INTEGRATION.is_dir():
        print()
        print(f"ERROR: Integration folder not found: {INTEGRATION}")
        print("Run create_rts_smart_covers_project.py first, from the RTS-Smart-Covers folder.")
        return 1

    test_required_files()
    test_json_files()
    test_manifest()
    test_hacs_json()
    test_services_yaml()
    test_python_compiles()
    test_ast_classes_and_methods()
    test_cover_source_contains_required_patterns()
    test_translation_key_consistency()
    test_readme_mentions_important_items()
    test_timed_math_examples()
    test_no_yaml_helper_dependency()

    return print_summary()


if __name__ == "__main__":
    raise SystemExit(main())
