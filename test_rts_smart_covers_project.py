"""Static project tests for RTS Smart Covers."""

from __future__ import annotations

import ast
import json
import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOMAIN = "rts_smart_covers"
INTEGRATION_DIR = ROOT / "custom_components" / DOMAIN


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def line_count(path: Path) -> int:
    return len(read(path).splitlines())


def load_json(path: Path) -> dict:
    return json.loads(read(path))


def test_required_files() -> None:
    required = [
        ROOT / "README.md",
        ROOT / "hacs.json",
        ROOT / "LICENSE",
        ROOT / ".gitignore",
        ROOT / ".gitattributes",
        INTEGRATION_DIR / "__init__.py",
        INTEGRATION_DIR / "manifest.json",
        INTEGRATION_DIR / "const.py",
        INTEGRATION_DIR / "config_flow.py",
        INTEGRATION_DIR / "cover.py",
        INTEGRATION_DIR / "services.yaml",
        INTEGRATION_DIR / "strings.json",
        INTEGRATION_DIR / "translations" / "en.json",
        INTEGRATION_DIR / "translations" / "sv.json",
        INTEGRATION_DIR / "brand" / ".gitkeep",
    ]
    for path in required:
        assert_true(path.exists(), f"Missing required file: {path}")
    assert_true(not (ROOT / "brand").exists(), "Root brand/ folder must not exist")


def test_gitattributes() -> None:
    gitattributes = read(ROOT / ".gitattributes")
    for needle in [
        "*.py text eol=lf",
        "*.json text eol=lf",
        "*.yaml text eol=lf",
        ".gitignore text eol=lf",
        ".gitattributes text eol=lf",
    ]:
        assert_true(needle in gitattributes, f".gitattributes missing {needle}")


def test_newlines() -> None:
    files = [
        ROOT / ".gitignore",
        ROOT / ".gitattributes",
        INTEGRATION_DIR / "__init__.py",
        INTEGRATION_DIR / "const.py",
        INTEGRATION_DIR / "config_flow.py",
        INTEGRATION_DIR / "cover.py",
        INTEGRATION_DIR / "services.yaml",
    ]
    for path in files:
        assert_true(line_count(path) > 5, f"{path} looks minified or missing newlines")
    cover = read(INTEGRATION_DIR / "cover.py")
    assert_true(
        '"""Cover platform for RTS Smart Covers."""\n\nfrom __future__ import annotations' in cover,
        "cover.py must have module docstring followed by newline before future import",
    )


def test_json() -> None:
    manifest = load_json(INTEGRATION_DIR / "manifest.json")
    hacs = load_json(ROOT / "hacs.json")
    load_json(INTEGRATION_DIR / "strings.json")
    load_json(INTEGRATION_DIR / "translations" / "en.json")
    load_json(INTEGRATION_DIR / "translations" / "sv.json")
    assert_true(manifest["domain"] == DOMAIN, "manifest domain mismatch")
    assert_true(manifest["name"] == "RTS Smart Covers", "manifest name mismatch")
    assert_true(manifest["config_flow"] is True, "manifest config_flow must be true")
    assert_true(manifest["iot_class"] == "local_push", "manifest iot_class mismatch")
    assert_true(manifest["version"].count(".") == 2, "manifest version must be semver-like")
    assert_true(hacs["homeassistant"] == "2026.6.1", "hacs minimum HA version mismatch")
    assert_true("cover" in hacs["domains"], "hacs domains must include cover")


def test_reconfigure_text() -> None:
    strings = read(INTEGRATION_DIR / "strings.json")
    en = read(INTEGRATION_DIR / "translations" / "en.json")
    sv = read(INTEGRATION_DIR / "translations" / "sv.json")
    readme = read(ROOT / "README.md")

    assert_true("Source cover (cannot be changed)" in strings, "strings.json reconfigure source-cover label is unclear")
    assert_true("Source cover (cannot be changed)" in en, "en.json reconfigure source-cover label is unclear")
    assert_true("cannot be changed here" in en, "en.json must explain source_cover cannot be changed")
    assert_true("Käll-cover (kan inte ändras)" in sv, "sv.json reconfigure source-cover label is unclear")
    assert_true("Käll-covern kan inte ändras här" in sv, "sv.json must explain source_cover cannot be changed")
    assert_true("source cover is used as the config entry unique ID" in readme, "README must explain source-cover limitation")


def test_python_compiles_and_ast() -> None:
    for path in [
        INTEGRATION_DIR / "__init__.py",
        INTEGRATION_DIR / "const.py",
        INTEGRATION_DIR / "config_flow.py",
        INTEGRATION_DIR / "cover.py",
    ]:
        py_compile.compile(str(path), doraise=True)
        ast.parse(read(path))


def test_cover_code_patterns() -> None:
    cover = read(INTEGRATION_DIR / "cover.py")
    required = [
        "CoverEntity",
        "RestoreEntity",
        "CoverDeviceClass.SHADE",
        "CoverEntityFeature.SET_POSITION",
        "current_cover_position",
        "async_set_cover_position",
        "async_call_later",
        "async_track_state_change_event",
        "monotonic",
        "STATE_UNAVAILABLE",
        "STATE_UNKNOWN",
        "async_set_known_position",
        "async_mark_open",
        "async_mark_closed",
        '"open_cover"',
        '"close_cover"',
        '"stop_cover"',
    ]
    for needle in required:
        assert_true(needle in cover, f"cover.py missing {needle}")
    forbidden = ["input_number.", "input_select.", "input_datetime.", "template:", "script."]
    for needle in forbidden:
        assert_true(needle not in cover, f"cover.py must not depend on {needle}")


def test_config_flow_patterns() -> None:
    config_flow = read(INTEGRATION_DIR / "config_flow.py")
    required = [
        "async_step_user",
        "async_step_reconfigure",
        "async_update_reload_and_abort",
        "_abort_if_unique_id_mismatch",
        "_abort_if_unique_id_configured",
        "EntitySelector",
        'EntitySelectorConfig(domain="cover")',
        "TextSelector",
        "NumberSelector",
        "NumberSelectorMode.BOX",
        "NumberSelectorMode.SLIDER",
    ]
    for needle in required:
        assert_true(needle in config_flow, f"config_flow.py missing {needle}")


def test_services() -> None:
    services = read(INTEGRATION_DIR / "services.yaml")
    init = read(INTEGRATION_DIR / "__init__.py")
    for service in ["set_known_position:", "mark_open:", "mark_closed:"]:
        assert_true(service in services, f"services.yaml missing {service}")
    for needle in [
        "hass.services.async_register",
        "SERVICE_SET_KNOWN_POSITION",
        "SERVICE_MARK_OPEN",
        "SERVICE_MARK_CLOSED",
        "async_set_known_position",
        "async_mark_open",
        "async_mark_closed",
    ]:
        assert_true(needle in init, f"__init__.py missing {needle}")


def test_timing_math() -> None:
    travel_time = 35.0
    assert_true(abs((abs(30 - 100) / 100 * travel_time) - 24.5) < 0.0001, "100->30 math failed")
    assert_true(abs((abs(30 - 0) / 100 * travel_time) - 10.5) < 0.0001, "0->30 math failed")
    assert_true(abs((abs(70 - 30) / 100 * travel_time) - 14.0) < 0.0001, "30->70 math failed")
    assert_true(abs((abs(0 - 70) / 100 * travel_time) - 24.5) < 0.0001, "70->0 math failed")
    assert_true(abs((abs(100 - 0) / 100 * travel_time) - 35.0) < 0.0001, "0->100 math failed")


def main() -> None:
    tests = [
        test_required_files,
        test_newlines,
        test_gitattributes,
        test_json,
        test_reconfigure_text,
        test_python_compiles_and_ast,
        test_cover_code_patterns,
        test_config_flow_patterns,
        test_services,
        test_timing_math,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print("\nAll RTS Smart Covers static tests passed.")


if __name__ == "__main__":
    main()
