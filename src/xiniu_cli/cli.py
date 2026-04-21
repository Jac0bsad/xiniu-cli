import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from dotenv import load_dotenv

DEFAULT_SERVER_BASE_URL = "http://vip.xiniudata.com/mcp"
KNOWN_COMMANDS = {"list-tools", "describe", "call", "config"}
CONFIG_ENV_VAR = "XINIU_CONFIG_PATH"
API_KEY_ENV_VAR = "XINIU_API_KEY"
SERVER_URL_ENV_VAR = "XINIU_MCP_URL"


def load_local_env() -> None:
    # This lets local development use a project-level .env without affecting
    # installed-user workflows.
    load_dotenv()


def get_default_config_path() -> Path:
    config_home = os.environ.get("XDG_CONFIG_HOME")
    if config_home:
        return Path(config_home) / "xiniu" / "config.json"
    return Path.home() / ".config" / "xiniu" / "config.json"


def get_config_path() -> Path:
    explicit_path = os.environ.get(CONFIG_ENV_VAR)
    if explicit_path:
        return Path(explicit_path).expanduser()
    return get_default_config_path()


def load_config() -> dict[str, Any]:
    config_path = get_config_path()
    if not config_path.exists():
        return {}

    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid config JSON in {config_path}: {exc}") from exc


def save_config(config: dict[str, Any]) -> Path:
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return config_path


def mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"


def with_api_key(url: str, api_key: str) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["api_key"] = api_key
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )


def get_server_url(explicit_url: str | None, explicit_api_key: str | None) -> str:
    config = load_config()

    server_url = (
        explicit_url
        or os.environ.get(SERVER_URL_ENV_VAR)
        or config.get("server_url")
        or DEFAULT_SERVER_BASE_URL
    )
    api_key = (
        explicit_api_key or os.environ.get(API_KEY_ENV_VAR) or config.get("api_key")
    )

    if "api_key=" in server_url:
        return server_url

    if not api_key:
        config_path = get_config_path()
        raise ValueError(
            "Missing API key. Set it with `xiniu config set-api-key <key>`, "
            f"export {API_KEY_ENV_VAR}=... , add it to a local .env for development, "
            "or pass `--api-key`."
            f" Config file path: {config_path}"
        )

    return with_api_key(server_url, api_key)


def parse_json_value(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def load_json_file_payload(file_path: str) -> dict[str, Any]:
    payload = json.loads(Path(file_path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("--json-file must contain a JSON object.")
    return payload


def parse_key_value_pairs(pairs: list[str]) -> dict[str, Any]:
    arguments: dict[str, Any] = {}
    for pair in pairs:
        if "=" not in pair:
            raise ValueError(f"Invalid --arg value: {pair!r}. Expected KEY=VALUE.")
        key, raw_value = pair.split("=", 1)
        if not key:
            raise ValueError(f"Invalid --arg value: {pair!r}. KEY cannot be empty.")
        arguments[key] = parse_json_value(raw_value)
    return arguments


def build_call_arguments(
    json_payload: str | None,
    json_file: str | None,
    pairs: list[str],
) -> dict[str, Any] | None:
    input_modes = [
        json_payload is not None,
        json_file is not None,
        bool(pairs),
    ]
    if sum(input_modes) > 1:
        raise ValueError("Use only one of --json, --json-file, or --arg.")

    if json_payload:
        payload = json.loads(json_payload)
        if not isinstance(payload, dict):
            raise ValueError("--json must decode to an object.")
        return payload

    if json_file:
        return load_json_file_payload(json_file)

    if pairs:
        return parse_key_value_pairs(pairs)

    return None


def compact_tool_summary(tool: Any) -> str:
    schema = tool.inputSchema or {}
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    if not properties:
        return "no arguments"

    parts = []
    for name in properties:
        suffix = "required" if name in required else "optional"
        parts.append(f"{name} ({suffix})")
    return ", ".join(parts)


async def list_all_tools(url: str) -> list[Any]:
    tools: list[Any] = []
    cursor: str | None = None

    async with streamable_http_client(url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            while True:
                result = await session.list_tools(cursor=cursor)
                tools.extend(result.tools)
                cursor = result.nextCursor
                if not cursor:
                    break

    return tools


async def describe_tool(url: str, tool_name: str) -> dict[str, Any]:
    tools = await list_all_tools(url)
    for tool in tools:
        if tool.name == tool_name:
            return tool.model_dump(mode="json", exclude_none=True)
    raise ValueError(f"Tool not found: {tool_name}")


async def call_tool(
    url: str,
    tool_name: str,
    arguments: dict[str, Any] | None,
) -> dict[str, Any]:
    async with streamable_http_client(url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments=arguments)
            return result.model_dump(mode="json", exclude_none=True)


def render_tool_result(result: dict[str, Any]) -> str:
    structured = result.get("structuredContent")
    content = result.get("content", [])

    if structured is not None:
        return json.dumps(structured, ensure_ascii=False, indent=2)

    if len(content) == 1 and content[0].get("type") == "text":
        return content[0].get("text", "")

    return json.dumps(result, ensure_ascii=False, indent=2)


def normalize_argv(argv: list[str]) -> list[str]:
    if not argv:
        return argv

    first = argv[0]
    if first.startswith("-") or first in KNOWN_COMMANDS:
        return argv

    return ["call", first, *argv[1:]]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Connect to the Xiniu MCP server over streamablehttp and expose "
            "remote tools as CLI commands."
        ),
        epilog=(
            "Shortcut: you can call a remote tool directly, for example "
            "`xiniu get_company_info --arg firm_name=...`."
        ),
    )
    parser.add_argument(
        "--server-url",
        help=(
            "MCP server URL. Defaults to XINIU_MCP_URL, config file, or the "
            "built-in Xiniu MCP base URL."
        ),
    )
    parser.add_argument(
        "--api-key",
        help=(
            "Xiniu API key. Defaults to XINIU_API_KEY, local .env, or the "
            "user config file."
        ),
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list-tools", help="List available MCP tools.")
    list_parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full tool definitions as JSON.",
    )

    describe_parser = subparsers.add_parser(
        "describe",
        help="Show one tool's schema and metadata.",
    )
    describe_parser.add_argument("tool_name", help="Remote tool name.")

    call_parser = subparsers.add_parser(
        "call",
        help="Call a remote tool with JSON or KEY=VALUE arguments.",
    )
    call_parser.add_argument("tool_name", help="Remote tool name.")
    call_parser.add_argument(
        "--json",
        dest="json_payload",
        help='JSON object payload, for example: \'{"firm_name":"..."}\'',
    )
    call_parser.add_argument(
        "--json-file",
        help="Read a JSON object payload from a file.",
    )
    call_parser.add_argument(
        "--arg",
        action="append",
        default=[],
        help=(
            "Tool argument in KEY=VALUE form. VALUE can be raw text or JSON, "
            'for example --arg limit=5 or --arg names=\'["A","B"]\'.'
        ),
    )
    call_parser.add_argument(
        "--raw",
        action="store_true",
        help="Print the full MCP call result JSON instead of a simplified view.",
    )

    config_parser = subparsers.add_parser(
        "config",
        help="Manage local Xiniu CLI configuration.",
    )
    config_subparsers = config_parser.add_subparsers(
        dest="config_command",
        required=True,
    )

    config_set_api_key_parser = config_subparsers.add_parser(
        "set-api-key",
        help="Persist the API key in the local user config file.",
    )
    config_set_api_key_parser.add_argument("api_key", help="Xiniu API key.")

    config_set_url_parser = config_subparsers.add_parser(
        "set-server-url",
        help="Persist a custom MCP server URL in the local user config file.",
    )
    config_set_url_parser.add_argument("server_url", help="MCP server URL.")

    config_show_parser = config_subparsers.add_parser(
        "show",
        help="Show the resolved config sources and masked values.",
    )
    config_show_parser.add_argument(
        "--json",
        action="store_true",
        help="Print config info as JSON.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    load_local_env()
    normalized_argv = normalize_argv(list(sys.argv[1:] if argv is None else argv))
    parser = build_parser()

    try:
        args = parser.parse_args(normalized_argv)
        config = load_config()

        if args.command == "config":
            if args.config_command == "set-api-key":
                config["api_key"] = args.api_key
                config_path = save_config(config)
                print(f"Saved API key to {config_path}")
                return 0

            if args.config_command == "set-server-url":
                config["server_url"] = args.server_url
                config_path = save_config(config)
                print(f"Saved server URL to {config_path}")
                return 0

            if args.config_command == "show":
                payload = {
                    "config_path": str(get_config_path()),
                    "resolved": {
                        "api_key": mask_secret(
                            args.api_key
                            or os.environ.get(API_KEY_ENV_VAR)
                            or config.get("api_key")
                        ),
                        "server_url": (
                            args.server_url
                            or os.environ.get(SERVER_URL_ENV_VAR)
                            or config.get("server_url")
                            or DEFAULT_SERVER_BASE_URL
                        ),
                    },
                    "sources": {
                        "api_key": (
                            "cli"
                            if args.api_key
                            else (
                                "env/.env"
                                if os.environ.get(API_KEY_ENV_VAR)
                                else "config" if config.get("api_key") else "missing"
                            )
                        ),
                        "server_url": (
                            "cli"
                            if args.server_url
                            else (
                                "env"
                                if os.environ.get(SERVER_URL_ENV_VAR)
                                else "config" if config.get("server_url") else "default"
                            )
                        ),
                    },
                }
                if args.json:
                    print(json.dumps(payload, ensure_ascii=False, indent=2))
                else:
                    print(f"config_path: {payload['config_path']}")
                    print(f"api_key: {payload['resolved']['api_key'] or 'missing'}")
                    print(f"api_key_source: {payload['sources']['api_key']}")
                    print(f"server_url: {payload['resolved']['server_url']}")
                    print(f"server_url_source: {payload['sources']['server_url']}")
                return 0

        server_url = get_server_url(args.server_url, args.api_key)

        if args.command == "list-tools":
            tools = asyncio.run(list_all_tools(server_url))
            if args.json:
                payload = [
                    tool.model_dump(mode="json", exclude_none=True) for tool in tools
                ]
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                for tool in tools:
                    print(f"{tool.name}: {tool.description or 'No description'}")
                    print(f"  args: {compact_tool_summary(tool)}")
            return 0

        if args.command == "describe":
            tool = asyncio.run(describe_tool(server_url, args.tool_name))
            print(json.dumps(tool, ensure_ascii=False, indent=2))
            return 0

        if args.command == "call":
            call_args = build_call_arguments(
                args.json_payload,
                args.json_file,
                args.arg,
            )
            result = asyncio.run(call_tool(server_url, args.tool_name, call_args))
            if args.raw:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(render_tool_result(result))
            return 0

        parser.error(f"Unsupported command: {args.command}")
        return 2
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
