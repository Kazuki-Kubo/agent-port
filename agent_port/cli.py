"""agent-port の CLI を提供する。"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import sys

from agent_port.app import build_startup_summary, configure_logging, run_application
from agent_port.config import AppConfig, ConfigError


@dataclass(frozen=True)
class SetupItem:
    """`setup` の結果 1 件を表す。

    Attributes
    ----------
    source : Path
        テンプレート元ファイル。
    target : Path
        出力先ファイル。
    action : str
        実行した操作。
    """

    source: Path
    target: Path
    action: str


@dataclass(frozen=True)
class DoctorStatus:
    """`doctor` の診断結果を表す。

    Attributes
    ----------
    ok : bool
        全体結果。
    base_dir : Path
        調査対象ディレクトリ。
    dotenv_path : Path
        `.env` のパス。
    dotenv_exists : bool
        `.env` が存在するか。
    workspace_file : Path | None
        workspace registry ファイル。
    workspace_file_exists : bool | None
        registry ファイルが存在するか。
    config_ok : bool
        `AppConfig` の構築に成功したか。
    config_error : str | None
        設定エラー内容。
    codex_command : str
        設定上の Codex コマンド。
    codex_path : Path | None
        解決できた Codex 実行ファイル。
    default_agent : str | None
        既定 agent。
    default_workspace : str | None
        既定 workspace ID。
    workspace_dir : Path | None
        既定 workspace の実パス。
    workspace_count : int | None
        登録 workspace 数。
    hint : str | None
        補助メッセージ。
    """

    ok: bool
    base_dir: Path
    dotenv_path: Path
    dotenv_exists: bool
    workspace_file: Path | None
    workspace_file_exists: bool | None
    config_ok: bool
    config_error: str | None
    codex_command: str
    codex_path: Path | None
    default_agent: str | None
    default_workspace: str | None
    workspace_dir: Path | None
    workspace_count: int | None
    hint: str | None


def main(argv: list[str] | None = None) -> int:
    """CLI を実行する。

    Parameters
    ----------
    argv : list[str] | None, default=None
        解析対象の引数一覧。

    Returns
    -------
    int
        終了コード。
    """

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None or args.command == "gateway":
        return run_gateway()
    if args.command == "config":
        return run_config(args)
    if args.command == "workspace":
        return run_workspace(args)
    if args.command == "setup":
        return run_setup(force=args.force)
    if args.command == "doctor":
        return run_doctor(json_output=args.json_output)

    parser.print_help()
    return 1


def build_parser() -> argparse.ArgumentParser:
    """CLI パーサーを作る。

    Returns
    -------
    argparse.ArgumentParser
        構築済みパーサー。
    """

    parser = argparse.ArgumentParser(
        prog="agent-port",
        description="Discord と Agent を中継する control plane CLI",
    )
    sub = parser.add_subparsers(dest="command")

    gateway = sub.add_parser("gateway", help="Gateway を起動する")
    gateway_sub = gateway.add_subparsers(dest="gateway_command")
    gateway_sub.add_parser("run", help="Gateway を起動する")

    config = sub.add_parser("config", help="設定を確認する")
    config_sub = config.add_subparsers(dest="config_command", required=True)
    config_sub.add_parser("file", help="使用中の workspace registry を表示する")
    config_show = config_sub.add_parser("show", help="現在の設定を表示する")
    config_show.add_argument("--json", action="store_true", dest="json_output")
    config_check = config_sub.add_parser("validate", help="設定を検証する")
    config_check.add_argument("--json", action="store_true", dest="json_output")

    workspace = sub.add_parser("workspace", help="workspace を確認する")
    workspace_sub = workspace.add_subparsers(dest="workspace_command", required=True)
    ws_list = workspace_sub.add_parser("list", help="workspace 一覧を表示する")
    ws_list.add_argument("--json", action="store_true", dest="json_output")
    ws_show = workspace_sub.add_parser("show", help="workspace 詳細を表示する")
    ws_show.add_argument("workspace_id")
    ws_show.add_argument("--json", action="store_true", dest="json_output")

    setup = sub.add_parser("setup", help="テンプレート設定ファイルを作る")
    setup.add_argument(
        "--force",
        action="store_true",
        help="一般設定ファイルだけ上書きする。.env は保護する",
    )

    doctor = sub.add_parser("doctor", help="起動状態を診断する")
    doctor.add_argument("--json", action="store_true", dest="json_output")

    return parser


def run_gateway() -> int:
    """Gateway を起動する。

    Returns
    -------
    int
        正常終了時は 0。
    """

    config = AppConfig.from_env()
    configure_logging(config.log_level)
    print(build_startup_summary(config))
    run_application(config)
    return 0


def run_config(args: argparse.Namespace) -> int:
    """`config` サブコマンドを処理する。

    Parameters
    ----------
    args : argparse.Namespace
        解析済み引数。

    Returns
    -------
    int
        終了コード。
    """

    if args.config_command == "file":
        return show_config_file()
    if args.config_command == "show":
        return show_config(args.json_output)
    if args.config_command == "validate":
        return validate_config(args.json_output)
    return 1


def run_workspace(args: argparse.Namespace) -> int:
    """`workspace` サブコマンドを処理する。

    Parameters
    ----------
    args : argparse.Namespace
        解析済み引数。

    Returns
    -------
    int
        終了コード。
    """

    if args.workspace_command == "list":
        return list_workspaces(args.json_output)
    if args.workspace_command == "show":
        return show_workspace(args.workspace_id, args.json_output)
    return 1


def run_setup(force: bool) -> int:
    """テンプレート設定ファイルを作る。

    Parameters
    ----------
    force : bool
        一般設定ファイルの上書きを許可するか。

    Returns
    -------
    int
        終了コード。
    """

    base = Path.cwd().resolve()
    items = (
        ensure_file(
            source=base / ".env.example",
            target=base / ".env",
            force=force,
            allow_overwrite=False,
        ),
        ensure_file(
            source=base / "config" / "workspaces.json.example",
            target=base / "config" / "workspaces.json",
            force=force,
            allow_overwrite=True,
        ),
    )
    for item in items:
        print(format_setup_item(item, base))
    return 0


def run_doctor(json_output: bool) -> int:
    """診断結果を表示する。

    Parameters
    ----------
    json_output : bool
        JSON で出力するか。

    Returns
    -------
    int
        正常なら 0、異常なら 1。
    """

    status = build_doctor()
    if json_output:
        print(json.dumps(doctor_payload(status), ensure_ascii=False, indent=2))
    else:
        print(format_doctor(status))
    return 0 if status.ok else 1


def show_config_file() -> int:
    """使用中の workspace registry を表示する。

    Returns
    -------
    int
        終了コード。
    """

    config = AppConfig.from_env()
    print(config.workspace_file or "(legacy env)")
    return 0


def show_config(json_output: bool) -> int:
    """現在の設定を表示する。

    Parameters
    ----------
    json_output : bool
        JSON で出力するか。

    Returns
    -------
    int
        終了コード。
    """

    config = AppConfig.from_env()
    payload = config_payload(config)
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_config(payload))
    return 0


def validate_config(json_output: bool) -> int:
    """設定を検証する。

    Parameters
    ----------
    json_output : bool
        JSON で出力するか。

    Returns
    -------
    int
        正常なら 0、異常なら 1。
    """

    try:
        config = AppConfig.from_env()
    except ConfigError as exc:
        payload = {"ok": False, "error": str(exc)}
        print(json.dumps(payload, ensure_ascii=False, indent=2) if json_output else f"invalid: {exc}")
        return 1

    payload = {
        "ok": True,
        "default_agent": config.default_agent,
        "default_workspace": config.default_workspace,
    }
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("valid")
        print(f"default_agent={config.default_agent}")
        print(f"default_workspace={config.default_workspace}")
    return 0


def list_workspaces(json_output: bool) -> int:
    """workspace 一覧を表示する。

    Parameters
    ----------
    json_output : bool
        JSON で出力するか。

    Returns
    -------
    int
        終了コード。
    """

    config = AppConfig.from_env()
    items = [workspace_payload(item) for item in config.workspaces.list()]
    if json_output:
        print(json.dumps(items, ensure_ascii=False, indent=2))
        return 0

    for item in items:
        agents = ",".join(item["allowed_agents"]) or "*"
        print(f"{item['id']}\t{item['path']}\tagents={agents}")
    return 0


def show_workspace(workspace_id: str, json_output: bool) -> int:
    """workspace 詳細を表示する。

    Parameters
    ----------
    workspace_id : str
        表示する workspace ID。
    json_output : bool
        JSON で出力するか。

    Returns
    -------
    int
        終了コード。
    """

    config = AppConfig.from_env()
    payload = workspace_payload(config.workspaces.get(workspace_id))
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"id={payload['id']}")
        print(f"path={payload['path']}")
        print(f"allowed_agents={','.join(payload['allowed_agents']) or '*'}")
        print(f"description={payload['description'] or ''}")
    return 0


def build_doctor(base_dir: Path | None = None) -> DoctorStatus:
    """診断結果を組み立てる。

    Parameters
    ----------
    base_dir : Path | None, default=None
        診断対象ディレクトリ。

    Returns
    -------
    DoctorStatus
        診断結果。
    """

    base = (base_dir or Path.cwd()).resolve()
    dotenv_path = base / ".env"
    dotenv_exists = dotenv_path.exists()

    try:
        config = AppConfig.from_env(base)
    except ConfigError as exc:
        codex_command = os.getenv("AGENT_PORT_CODEX_COMMAND", "codex").strip() or "codex"
        codex_path = resolve_command(codex_command, base)
        workspace_file, workspace_file_exists = infer_workspace_file(base)
        hint = build_hint(
            dotenv_exists=dotenv_exists,
            workspace_file_exists=workspace_file_exists,
            config_ok=False,
            codex_path=codex_path,
        )
        return DoctorStatus(
            ok=False,
            base_dir=base,
            dotenv_path=dotenv_path,
            dotenv_exists=dotenv_exists,
            workspace_file=workspace_file,
            workspace_file_exists=workspace_file_exists,
            config_ok=False,
            config_error=str(exc),
            codex_command=codex_command,
            codex_path=codex_path,
            default_agent=None,
            default_workspace=None,
            workspace_dir=None,
            workspace_count=None,
            hint=hint,
        )

    codex_path = resolve_command(config.codex_command, base)
    workspace_file = config.workspace_file
    workspace_file_exists = workspace_file.exists() if workspace_file is not None else None
    hint = build_hint(
        dotenv_exists=dotenv_exists,
        workspace_file_exists=workspace_file_exists,
        config_ok=True,
        codex_path=codex_path,
    )
    return DoctorStatus(
        ok=codex_path is not None,
        base_dir=base,
        dotenv_path=dotenv_path,
        dotenv_exists=dotenv_exists,
        workspace_file=workspace_file,
        workspace_file_exists=workspace_file_exists,
        config_ok=True,
        config_error=None,
        codex_command=config.codex_command,
        codex_path=codex_path,
        default_agent=config.default_agent,
        default_workspace=config.default_workspace,
        workspace_dir=config.workspace,
        workspace_count=len(config.list_workspace_ids()),
        hint=hint,
    )


def ensure_file(
    source: Path,
    target: Path,
    force: bool,
    allow_overwrite: bool,
) -> SetupItem:
    """テンプレートファイルを必要に応じて配置する。

    Parameters
    ----------
    source : Path
        テンプレート元。
    target : Path
        出力先。
    force : bool
        上書き許可フラグ。
    allow_overwrite : bool
        このファイルを上書きしてよいか。

    Returns
    -------
    SetupItem
        実行結果。
    """

    if not source.exists():
        return SetupItem(source=source, target=target, action="missing_template")

    exists = target.exists()
    if exists and force and not allow_overwrite:
        return SetupItem(source=source, target=target, action="protected")
    if exists and not force:
        return SetupItem(source=source, target=target, action="kept")

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    action = "overwritten" if exists and force else "created"
    return SetupItem(source=source, target=target, action=action)


def format_setup_item(item: SetupItem, base_dir: Path) -> str:
    """`setup` の結果を文字列にする。

    Parameters
    ----------
    item : SetupItem
        表示対象の結果。
    base_dir : Path
        相対表示の基準。

    Returns
    -------
    str
        表示用の 1 行文字列。
    """

    target = display_path(item.target, base_dir)
    source = display_path(item.source, base_dir)
    if item.action == "created":
        return f"created {target} from {source}"
    if item.action == "overwritten":
        return f"overwritten {target} from {source}"
    if item.action == "kept":
        return f"kept {target}"
    if item.action == "protected":
        return f"protected {target}"
    return f"missing template {source}"


def build_hint(
    dotenv_exists: bool,
    workspace_file_exists: bool | None,
    config_ok: bool,
    codex_path: Path | None,
) -> str | None:
    """診断結果に応じた補助メッセージを返す。

    Parameters
    ----------
    dotenv_exists : bool
        `.env` があるか。
    workspace_file_exists : bool | None
        registry があるか。
    config_ok : bool
        設定読込に成功したか。
    codex_path : Path | None
        Codex 実行ファイルを解決できたか。

    Returns
    -------
    str | None
        必要なら補助メッセージ。
    """

    if not dotenv_exists or workspace_file_exists is False:
        return "uv run agent-port setup で雛形を作成してから設定してください。"
    if not config_ok:
        return ".env と config/workspaces.json の内容を確認してください。"
    if codex_path is None:
        return "Codex CLI をインストールするか AGENT_PORT_CODEX_COMMAND を見直してください。"
    return None


def infer_workspace_file(base_dir: Path) -> tuple[Path | None, bool | None]:
    """workspace registry の推定パスを返す。

    Parameters
    ----------
    base_dir : Path
        基準ディレクトリ。

    Returns
    -------
    tuple[Path | None, bool | None]
        推定パスと存在有無。
    """

    file_env = os.getenv("AGENT_PORT_WORKSPACE_REGISTRY", "").strip()
    legacy = (
        os.getenv("AGENT_PORT_CODEX_WORKSPACE", "").strip()
        or os.getenv("AGENT_PORT_AGENT_WORKSPACE", "").strip()
    )
    if file_env:
        path = Path(file_env)
        resolved = path.resolve() if path.is_absolute() else (base_dir / path).resolve()
        return resolved, resolved.exists()
    if legacy:
        return None, None

    path = (base_dir / "config" / "workspaces.json").resolve()
    return path, path.exists()


def resolve_command(command: str, base_dir: Path) -> Path | None:
    """コマンドの実体パスを解決する。

    Parameters
    ----------
    command : str
        コマンド文字列。
    base_dir : Path
        相対パス解決の基準。

    Returns
    -------
    Path | None
        解決できたパス。見つからなければ `None`。
    """

    if not command.strip():
        return None
    if "/" in command or "\\" in command:
        path = Path(command)
        resolved = path.resolve() if path.is_absolute() else (base_dir / path).resolve()
        return resolved if resolved.exists() else None

    resolved = shutil.which(command)
    return Path(resolved).resolve() if resolved else None


def config_payload(config: AppConfig) -> dict[str, object]:
    """設定を表示用 dict に変換する。

    Parameters
    ----------
    config : AppConfig
        変換対象の設定。

    Returns
    -------
    dict[str, object]
        表示用データ。
    """

    return {
        "base_dir": str(config.base_dir),
        "chat": config.chat,
        "default_agent": config.default_agent,
        "default_workspace": config.default_workspace,
        "workspace_file": str(config.workspace_file) if config.workspace_file else None,
        "discord_trigger": config.discord_trigger,
        "codex_command": config.codex_command,
        "codex_timeout": config.codex_timeout,
        "log_level": config.log_level,
        "workspace_ids": list(config.list_workspace_ids()),
    }


def workspace_payload(workspace) -> dict[str, object]:
    """workspace を表示用 dict に変換する。

    Parameters
    ----------
    workspace : object
        `Workspace` 相当のオブジェクト。

    Returns
    -------
    dict[str, object]
        表示用データ。
    """

    return {
        "id": workspace.workspace_id,
        "path": str(workspace.path),
        "allowed_agents": list(workspace.allowed_agents),
        "description": workspace.description,
    }


def doctor_payload(status: DoctorStatus) -> dict[str, object]:
    """診断結果を JSON 用 dict に変換する。

    Parameters
    ----------
    status : DoctorStatus
        診断結果。

    Returns
    -------
    dict[str, object]
        JSON 用データ。
    """

    return {
        "ok": status.ok,
        "base_dir": str(status.base_dir),
        "dotenv_path": str(status.dotenv_path),
        "dotenv_exists": status.dotenv_exists,
        "workspace_file": str(status.workspace_file) if status.workspace_file else None,
        "workspace_file_exists": status.workspace_file_exists,
        "config_ok": status.config_ok,
        "config_error": status.config_error,
        "codex_command": status.codex_command,
        "codex_path": str(status.codex_path) if status.codex_path else None,
        "default_agent": status.default_agent,
        "default_workspace": status.default_workspace,
        "workspace_dir": str(status.workspace_dir) if status.workspace_dir else None,
        "workspace_count": status.workspace_count,
        "hint": status.hint,
    }


def format_config(payload: dict[str, object]) -> str:
    """設定表示文字列を作る。

    Parameters
    ----------
    payload : dict[str, object]
        表示対象データ。

    Returns
    -------
    str
        複数行文字列。
    """

    keys = [
        "base_dir",
        "chat",
        "default_agent",
        "default_workspace",
        "workspace_file",
        "discord_trigger",
        "codex_command",
        "codex_timeout",
        "log_level",
    ]
    lines = [f"{key}={payload[key]}" for key in keys]
    lines.append(f"workspace_ids={','.join(payload['workspace_ids'])}")
    return "\n".join(lines)


def format_doctor(status: DoctorStatus) -> str:
    """診断結果表示文字列を作る。

    Parameters
    ----------
    status : DoctorStatus
        診断結果。

    Returns
    -------
    str
        複数行文字列。
    """

    file_path = str(status.workspace_file) if status.workspace_file else "(legacy env)"
    file_exists = (
        str(status.workspace_file_exists)
        if status.workspace_file_exists is not None
        else "legacy"
    )
    workspace_dir = str(status.workspace_dir) if status.workspace_dir else ""
    codex_path = str(status.codex_path) if status.codex_path else ""

    lines = [
        "ok" if status.ok else "error",
        f"base_dir={status.base_dir}",
        f"dotenv_path={status.dotenv_path}",
        f"dotenv_exists={status.dotenv_exists}",
        f"workspace_file={file_path}",
        f"workspace_file_exists={file_exists}",
        f"config_ok={status.config_ok}",
        f"codex_command={status.codex_command}",
        f"codex_found={status.codex_path is not None}",
        f"codex_path={codex_path}",
        f"default_agent={status.default_agent or ''}",
        f"default_workspace={status.default_workspace or ''}",
        f"workspace_dir={workspace_dir}",
        f"workspace_count={status.workspace_count if status.workspace_count is not None else ''}",
    ]
    if status.config_error is not None:
        lines.append(f"config_error={status.config_error}")
    if status.hint is not None:
        lines.append(f"hint={status.hint}")
    return "\n".join(lines)


def display_path(path: Path, base_dir: Path) -> str:
    """表示用に相対パス化する。

    Parameters
    ----------
    path : Path
        表示対象パス。
    base_dir : Path
        相対化の基準。

    Returns
    -------
    str
        可能なら相対パス、無理なら絶対パス。
    """

    try:
        return str(path.relative_to(base_dir))
    except ValueError:
        return str(path)


SetupFileResult = SetupItem
DoctorReport = DoctorStatus
run_gateway_command = run_gateway
run_config_command = run_config
run_workspace_command = run_workspace
run_setup_command = run_setup
run_doctor_command = run_doctor
print_config_file = show_config_file
build_doctor_report = build_doctor
ensure_template_file = ensure_file
format_setup_result = format_setup_item
build_doctor_hint = build_hint
resolve_command_path = resolve_command
serialize_config = config_payload
serialize_workspace = workspace_payload
serialize_doctor_report = doctor_payload
format_config_payload = format_config
format_doctor_report = format_doctor
format_path_for_display = display_path
build_cli_parser = build_parser


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
