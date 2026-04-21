import json

from xiniu_cli.cli import main, normalize_argv


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
