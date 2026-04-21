import json
from pathlib import Path

import pytest

from xiniu_cli.cli import build_call_arguments, main, normalize_argv


def test_normalize_argv_treats_tool_name_as_call() -> None:
    assert normalize_argv(["get_company_info", "--arg", "firm_name=test"]) == [
        "call",
        "get_company_info",
        "--arg",
        "firm_name=test",
    ]


def test_config_show_json_works_without_local_config(capsys, monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XINIU_CONFIG_PATH", str(tmp_path / "config.json"))
    exit_code = main(["config", "show", "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["resolved"]["api_key"] is None
    assert payload["sources"]["server_url"] == "default"


def test_build_call_arguments_supports_json_file(tmp_path: Path) -> None:
    payload_file = tmp_path / "payload.json"
    payload_file.write_text('{"limit": 3, "req_params": []}', encoding="utf-8")

    assert build_call_arguments(None, str(payload_file), []) == {
        "limit": 3,
        "req_params": [],
    }


def test_build_call_arguments_rejects_multiple_input_modes(tmp_path: Path) -> None:
    payload_file = tmp_path / "payload.json"
    payload_file.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="Use only one"):
        build_call_arguments('{"limit": 1}', str(payload_file), [])


def test_build_call_arguments_rejects_non_object_json_file(tmp_path: Path) -> None:
    payload_file = tmp_path / "payload.json"
    payload_file.write_text('["invalid"]', encoding="utf-8")

    with pytest.raises(ValueError, match="--json-file must contain a JSON object"):
        build_call_arguments(None, str(payload_file), [])
