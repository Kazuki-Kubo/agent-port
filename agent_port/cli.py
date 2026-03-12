"""agent-port の CLI を提供するモジュール。"""

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
class SetupFileResult:
    """`setup` で扱う雛形ファイルの処理結果を表す。

    Attributes
    ----------
    source : Path
        コピー元の雛形ファイル。
    target : Path
        配置先の実ファイル。
    action : str
        実施内容。`created`、`overwritten`、`kept`、`missing_template` のいずれか。
    """

    source: Path
    target: Path
    action: str


@dataclass(frozen=True)
class DoctorReport:
    """`doctor` で表示する診断結果を表す。

    Attributes
    ----------
    ok : bool
        全体として起動可能かどうか。
    base_dir : Path
        設定解決の基準ディレクトリ。
    dotenv_path : Path
        `.env` の想定パス。
    dotenv_exists : bool
        `.env` が存在するかどうか。
    workspace_registry_path : Path | None
        workspace registry のパス。legacy 設定時は `None`。
    workspace_registry_exists : bool | None
        workspace registry ファイルの存在有無。legacy 設定時は `None`。
    config_valid : bool
        `AppConfig` の構築に成功したかどうか。
    config_error : str | None
        設定不正時のエラーメッセージ。
    codex_command : str
        設定済みの Codex 実行コマンド。
    codex_command_path : Path | None
        解決できた Codex 実行ファイルのパス。
    default_agent_backend : str | None
        既定 Agent backend。
    default_workspace_id : str | None
        既定 workspace ID。
    default_workspace_path : Path | None
        既定 workspace の実パス。
    workspace_count : int | None
        読み込めた workspace 数。
    hint : str | None
        次の操作を示す短い案内。
    """

    ok: bool
    base_dir: Path
    dotenv_path: Path
    dotenv_exists: bool
    workspace_registry_path: Path | None
    workspace_registry_exists: bool | None
    config_valid: bool
    config_error: str | None
    codex_command: str
    codex_command_path: Path | None
    default_agent_backend: str | None
    default_workspace_id: str | None
    default_workspace_path: Path | None
    workspace_count: int | None
    hint: str | None


def main(argv: list[str] | None = None) -> int:
    """CLI を実行する。

    Parameters
    ----------
    argv : list[str] | None, default=None
        解析対象の引数一覧。`None` の場合は `sys.argv[1:]` を使う。

    Returns
    -------
    int
        終了コード。
    """

    parser = build_cli_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        return run_gateway_command()
    if args.command == "gateway":
        return run_gateway_command()
    if args.command == "config":
        return run_config_command(args=args)
    if args.command == "workspace":
        return run_workspace_command(args=args)
    if args.command == "setup":
        return run_setup_command(force=args.force)
    if args.command == "doctor":
        return run_doctor_command(json_output=args.json_output)

    parser.print_help()
    return 1


def build_cli_parser() -> argparse.ArgumentParser:
    """CLI パーサを構築する。

    Returns
    -------
    argparse.ArgumentParser
        `agent-port` 用の引数パーサ。
    """

    parser = argparse.ArgumentParser(
        prog="agent-port",
        description="Discord と Agent を中継する control plane CLI",
    )
    subparsers = parser.add_subparsers(dest="command")

    gateway_parser = subparsers.add_parser("gateway", help="Gateway を起動する")
    gateway_subparsers = gateway_parser.add_subparsers(dest="gateway_command")
    gateway_subparsers.add_parser("run", help="Gateway を前面起動する")

    config_parser = subparsers.add_parser("config", help="設定を確認する")
    config_subparsers = config_parser.add_subparsers(dest="config_command", required=True)
    config_subparsers.add_parser("file", help="現在の workspace registry の参照元を表示する")
    config_show_parser = config_subparsers.add_parser("show", help="現在の設定を表示する")
    config_show_parser.add_argument("--json", action="store_true", dest="json_output")
    config_validate_parser = config_subparsers.add_parser(
        "validate",
        help="現在の設定で起動可能か検証する",
    )
    config_validate_parser.add_argument("--json", action="store_true", dest="json_output")

    workspace_parser = subparsers.add_parser("workspace", help="workspace を確認する")
    workspace_subparsers = workspace_parser.add_subparsers(
        dest="workspace_command",
        required=True,
    )
    workspace_list_parser = workspace_subparsers.add_parser(
        "list",
        help="登録済み workspace 一覧を表示する",
    )
    workspace_list_parser.add_argument("--json", action="store_true", dest="json_output")
    workspace_show_parser = workspace_subparsers.add_parser(
        "show",
        help="指定 workspace の詳細を表示する",
    )
    workspace_show_parser.add_argument("workspace_id")
    workspace_show_parser.add_argument("--json", action="store_true", dest="json_output")

    setup_parser = subparsers.add_parser("setup", help="雛形ファイルを配置する")
    setup_parser.add_argument(
        "--force",
        action="store_true",
        help="既存ファイルがあっても雛形で上書きする",
    )

    doctor_parser = subparsers.add_parser("doctor", help="起動前の状態を診断する")
    doctor_parser.add_argument("--json", action="store_true", dest="json_output")

    return parser


def run_gateway_command() -> int:
    """Gateway 起動コマンドを実行する。

    Returns
    -------
    int
        正常終了時は `0`。
    """

    config = AppConfig.from_env()
    configure_logging(config.log_level)
    print(build_startup_summary(config))
    run_application(config)
    return 0


def run_config_command(args: argparse.Namespace) -> int:
    """設定確認コマンドを実行する。

    Parameters
    ----------
    args : argparse.Namespace
        解析済み CLI 引数。

    Returns
    -------
    int
        終了コード。
    """

    if args.config_command == "file":
        return print_config_file()
    if args.config_command == "show":
        return show_config(json_output=args.json_output)
    if args.config_command == "validate":
        return validate_config(json_output=args.json_output)
    return 1


def run_workspace_command(args: argparse.Namespace) -> int:
    """workspace 確認コマンドを実行する。

    Parameters
    ----------
    args : argparse.Namespace
        解析済み CLI 引数。

    Returns
    -------
    int
        終了コード。
    """

    if args.workspace_command == "list":
        return list_workspaces(json_output=args.json_output)
    if args.workspace_command == "show":
        return show_workspace(
            workspace_id=args.workspace_id,
            json_output=args.json_output,
        )
    return 1


def run_setup_command(force: bool) -> int:
    """雛形ファイルを配置する。

    Parameters
    ----------
    force : bool
        既存ファイルを上書きするかどうか。

    Returns
    -------
    int
        正常終了時は `0`。
    """

    base_dir = Path.cwd().resolve()
    results = (
        ensure_template_file(
            source=base_dir / ".env.example",
            target=base_dir / ".env",
            force=force,
        ),
        ensure_template_file(
            source=base_dir / "config" / "workspaces.json.example",
            target=base_dir / "config" / "workspaces.json",
            force=force,
        ),
    )
    for result in results:
        print(format_setup_result(result, base_dir=base_dir))
    return 0


def run_doctor_command(json_output: bool) -> int:
    """起動前の状態を診断する。

    Parameters
    ----------
    json_output : bool
        JSON 形式で出力するかどうか。

    Returns
    -------
    int
        診断が成功した場合は `0`、問題がある場合は `1`。
    """

    report = build_doctor_report()
    if json_output:
        print(json.dumps(serialize_doctor_report(report), ensure_ascii=False, indent=2))
    else:
        print(format_doctor_report(report))
    return 0 if report.ok else 1


def print_config_file() -> int:
    """現在の workspace registry パスを表示する。

    Returns
    -------
    int
        正常終了時は `0`。
    """

    config = AppConfig.from_env()
    print(config.workspace_registry_path or "(legacy env)")
    return 0


def show_config(json_output: bool) -> int:
    """現在の設定を表示する。

    Parameters
    ----------
    json_output : bool
        JSON 形式で出力するかどうか。

    Returns
    -------
    int
        正常終了時は `0`。
    """

    config = AppConfig.from_env()
    payload = serialize_config(config)
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_config_payload(payload))
    return 0


def validate_config(json_output: bool) -> int:
    """現在の設定が有効か検証する。

    Parameters
    ----------
    json_output : bool
        JSON 形式で出力するかどうか。

    Returns
    -------
    int
        正常なら `0`、不正なら `1`。
    """

    try:
        config = AppConfig.from_env()
    except ConfigError as exc:
        if json_output:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"invalid: {exc}")
        return 1

    payload = {
        "ok": True,
        "default_agent_backend": config.default_agent_backend,
        "default_workspace_id": config.default_workspace_id,
    }
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("valid")
        print(f"default_agent_backend={config.default_agent_backend}")
        print(f"default_workspace_id={config.default_workspace_id}")
    return 0


def list_workspaces(json_output: bool) -> int:
    """workspace 一覧を表示する。

    Parameters
    ----------
    json_output : bool
        JSON 形式で出力するかどうか。

    Returns
    -------
    int
        正常終了時は `0`。
    """

    config = AppConfig.from_env()
    workspaces = [serialize_workspace(workspace) for workspace in config.workspace_registry.list_workspaces()]
    if json_output:
        print(json.dumps(workspaces, ensure_ascii=False, indent=2))
        return 0

    for workspace in workspaces:
        print(
            f"{workspace['id']}\t{workspace['path']}\t"
            f"agents={','.join(workspace['allowed_agents']) or '*'}"
        )
    return 0


def show_workspace(workspace_id: str, json_output: bool) -> int:
    """指定 workspace の詳細を表示する。

    Parameters
    ----------
    workspace_id : str
        表示対象の workspace ID。
    json_output : bool
        JSON 形式で出力するかどうか。

    Returns
    -------
    int
        正常終了時は `0`。
    """

    config = AppConfig.from_env()
    workspace = config.workspace_registry.get_workspace(workspace_id)
    payload = serialize_workspace(workspace)
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"id={payload['id']}")
        print(f"path={payload['path']}")
        print(f"allowed_agents={','.join(payload['allowed_agents']) or '*'}")
        print(f"description={payload['description'] or ''}")
    return 0


def build_doctor_report(base_dir: Path | None = None) -> DoctorReport:
    """診断結果を構築する。

    Parameters
    ----------
    base_dir : Path | None, default=None
        診断対象の基準ディレクトリ。`None` の場合はカレントディレクトリを使う。

    Returns
    -------
    DoctorReport
        CLI 表示用の診断結果。
    """

    resolved_base_dir = (base_dir or Path.cwd()).resolve()
    dotenv_path = resolved_base_dir / ".env"
    dotenv_exists = dotenv_path.exists()

    try:
        config = AppConfig.from_env(base_dir=resolved_base_dir)
    except ConfigError as exc:
        codex_command = os.getenv("AGENT_PORT_CODEX_COMMAND", "codex").strip() or "codex"
        codex_command_path = resolve_command_path(codex_command, base_dir=resolved_base_dir)
        workspace_registry_env = os.getenv("AGENT_PORT_WORKSPACE_REGISTRY", "").strip()
        legacy_workspace_env = (
            os.getenv("AGENT_PORT_CODEX_WORKSPACE", "").strip()
            or os.getenv("AGENT_PORT_AGENT_WORKSPACE", "").strip()
        )
        if workspace_registry_env:
            workspace_registry_path = (resolved_base_dir / workspace_registry_env).resolve()
            workspace_registry_exists = workspace_registry_path.exists()
        elif legacy_workspace_env:
            workspace_registry_path = None
            workspace_registry_exists = None
        else:
            workspace_registry_path = resolved_base_dir / "config" / "workspaces.json"
            workspace_registry_exists = workspace_registry_path.exists()
        hint = build_doctor_hint(
            dotenv_exists=dotenv_exists,
            workspace_registry_exists=workspace_registry_exists,
            config_valid=False,
            codex_command_path=codex_command_path,
        )
        return DoctorReport(
            ok=False,
            base_dir=resolved_base_dir,
            dotenv_path=dotenv_path,
            dotenv_exists=dotenv_exists,
            workspace_registry_path=workspace_registry_path,
            workspace_registry_exists=workspace_registry_exists,
            config_valid=False,
            config_error=str(exc),
            codex_command=codex_command,
            codex_command_path=codex_command_path,
            default_agent_backend=None,
            default_workspace_id=None,
            default_workspace_path=None,
            workspace_count=None,
            hint=hint,
        )

    codex_command_path = resolve_command_path(
        command=config.codex_command,
        base_dir=resolved_base_dir,
    )
    workspace_registry_path = config.workspace_registry_path
    workspace_registry_exists = (
        workspace_registry_path.exists()
        if workspace_registry_path is not None
        else None
    )
    hint = build_doctor_hint(
        dotenv_exists=dotenv_exists,
        workspace_registry_exists=workspace_registry_exists,
        config_valid=True,
        codex_command_path=codex_command_path,
    )
    return DoctorReport(
        ok=codex_command_path is not None,
        base_dir=resolved_base_dir,
        dotenv_path=dotenv_path,
        dotenv_exists=dotenv_exists,
        workspace_registry_path=workspace_registry_path,
        workspace_registry_exists=workspace_registry_exists,
        config_valid=True,
        config_error=None,
        codex_command=config.codex_command,
        codex_command_path=codex_command_path,
        default_agent_backend=config.default_agent_backend,
        default_workspace_id=config.default_workspace_id,
        default_workspace_path=config.agent_workspace,
        workspace_count=len(config.list_workspace_ids()),
        hint=hint,
    )


def ensure_template_file(source: Path, target: Path, force: bool) -> SetupFileResult:
    """雛形ファイルを必要に応じて配置する。

    Parameters
    ----------
    source : Path
        コピー元の雛形ファイル。
    target : Path
        配置先ファイル。
    force : bool
        既存ファイルを上書きするかどうか。

    Returns
    -------
    SetupFileResult
        実施した処理内容。
    """

    if not source.exists():
        return SetupFileResult(source=source, target=target, action="missing_template")

    target_exists = target.exists()
    if target_exists and not force:
        return SetupFileResult(source=source, target=target, action="kept")

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    action = "overwritten" if target_exists and force else "created"
    return SetupFileResult(source=source, target=target, action=action)


def format_setup_result(result: SetupFileResult, base_dir: Path) -> str:
    """`setup` の処理結果を表示文へ変換する。

    Parameters
    ----------
    result : SetupFileResult
        表示対象の処理結果。
    base_dir : Path
        相対パス表示の基準ディレクトリ。

    Returns
    -------
    str
        1 行の表示文。
    """

    target_label = format_path_for_display(result.target, base_dir=base_dir)
    source_label = format_path_for_display(result.source, base_dir=base_dir)
    if result.action == "created":
        return f"created {target_label} from {source_label}"
    if result.action == "overwritten":
        return f"overwritten {target_label} from {source_label}"
    if result.action == "kept":
        return f"kept {target_label}"
    return f"missing template {source_label}"


def build_doctor_hint(
    dotenv_exists: bool,
    workspace_registry_exists: bool | None,
    config_valid: bool,
    codex_command_path: Path | None,
) -> str | None:
    """診断結果に応じた次の操作案内を返す。

    Parameters
    ----------
    dotenv_exists : bool
        `.env` が存在するかどうか。
    workspace_registry_exists : bool | None
        workspace registry ファイルの存在有無。legacy 設定時は `None`。
    config_valid : bool
        設定が妥当かどうか。
    codex_command_path : Path | None
        解決できた Codex 実行ファイルのパス。

    Returns
    -------
    str | None
        表示すべき案内。不要なら `None`。
    """

    if not dotenv_exists or workspace_registry_exists is False:
        return "uv run agent-port setup で雛形を配置してから設定してください。"
    if not config_valid:
        return ".env と config/workspaces.json の値を見直してください。"
    if codex_command_path is None:
        return "Codex CLI をインストールするか AGENT_PORT_CODEX_COMMAND を修正してください。"
    return None


def resolve_command_path(command: str, base_dir: Path) -> Path | None:
    """実行コマンドの実体パスを解決する。

    Parameters
    ----------
    command : str
        解決対象のコマンド文字列。
    base_dir : Path
        相対パス解決の基準ディレクトリ。

    Returns
    -------
    Path | None
        解決できたパス。見つからない場合は `None`。
    """

    if not command.strip():
        return None

    if "/" in command or "\\" in command:
        command_path = Path(command)
        resolved_path = (
            command_path.resolve()
            if command_path.is_absolute()
            else (base_dir / command_path).resolve()
        )
        return resolved_path if resolved_path.exists() else None

    resolved = shutil.which(command)
    return Path(resolved).resolve() if resolved else None


def serialize_config(config: AppConfig) -> dict[str, object]:
    """設定を CLI 表示用の辞書へ変換する。

    Parameters
    ----------
    config : AppConfig
        変換対象の設定。

    Returns
    -------
    dict[str, object]
        表示用の辞書。
    """

    return {
        "base_dir": str(config.base_dir),
        "chat_backend": config.chat_backend,
        "default_agent_backend": config.default_agent_backend,
        "default_workspace_id": config.default_workspace_id,
        "workspace_registry_path": (
            str(config.workspace_registry_path)
            if config.workspace_registry_path is not None
            else None
        ),
        "discord_trigger_mode": config.discord_trigger_mode,
        "codex_command": config.codex_command,
        "codex_timeout_seconds": config.codex_timeout_seconds,
        "log_level": config.log_level,
        "workspace_ids": list(config.list_workspace_ids()),
    }


def serialize_workspace(workspace) -> dict[str, object]:
    """workspace を CLI 表示用の辞書へ変換する。

    Parameters
    ----------
    workspace : object
        変換対象の workspace。

    Returns
    -------
    dict[str, object]
        表示用の辞書。
    """

    return {
        "id": workspace.workspace_id,
        "path": str(workspace.path),
        "allowed_agents": list(workspace.allowed_agents),
        "description": workspace.description,
    }


def serialize_doctor_report(report: DoctorReport) -> dict[str, object]:
    """診断結果を JSON 出力用の辞書へ変換する。

    Parameters
    ----------
    report : DoctorReport
        変換対象の診断結果。

    Returns
    -------
    dict[str, object]
        JSON 出力用の辞書。
    """

    return {
        "ok": report.ok,
        "base_dir": str(report.base_dir),
        "dotenv_path": str(report.dotenv_path),
        "dotenv_exists": report.dotenv_exists,
        "workspace_registry_path": (
            str(report.workspace_registry_path)
            if report.workspace_registry_path is not None
            else None
        ),
        "workspace_registry_exists": report.workspace_registry_exists,
        "config_valid": report.config_valid,
        "config_error": report.config_error,
        "codex_command": report.codex_command,
        "codex_command_path": (
            str(report.codex_command_path)
            if report.codex_command_path is not None
            else None
        ),
        "default_agent_backend": report.default_agent_backend,
        "default_workspace_id": report.default_workspace_id,
        "default_workspace_path": (
            str(report.default_workspace_path)
            if report.default_workspace_path is not None
            else None
        ),
        "workspace_count": report.workspace_count,
        "hint": report.hint,
    }


def format_config_payload(payload: dict[str, object]) -> str:
    """設定辞書を表示用テキストへ変換する。

    Parameters
    ----------
    payload : dict[str, object]
        表示対象の設定辞書。

    Returns
    -------
    str
        表示用テキスト。
    """

    ordered_keys = [
        "base_dir",
        "chat_backend",
        "default_agent_backend",
        "default_workspace_id",
        "workspace_registry_path",
        "discord_trigger_mode",
        "codex_command",
        "codex_timeout_seconds",
        "log_level",
    ]
    lines = [f"{key}={payload[key]}" for key in ordered_keys]
    lines.append(f"workspace_ids={','.join(payload['workspace_ids'])}")
    return "\n".join(lines)


def format_doctor_report(report: DoctorReport) -> str:
    """診断結果を表示用テキストへ変換する。

    Parameters
    ----------
    report : DoctorReport
        表示対象の診断結果。

    Returns
    -------
    str
        表示用テキスト。
    """

    workspace_registry_path = (
        str(report.workspace_registry_path)
        if report.workspace_registry_path is not None
        else "(legacy env)"
    )
    workspace_registry_exists = (
        str(report.workspace_registry_exists)
        if report.workspace_registry_exists is not None
        else "legacy"
    )
    default_workspace_path = (
        str(report.default_workspace_path)
        if report.default_workspace_path is not None
        else ""
    )
    codex_command_path = (
        str(report.codex_command_path)
        if report.codex_command_path is not None
        else ""
    )

    lines = [
        "ok" if report.ok else "error",
        f"base_dir={report.base_dir}",
        f"dotenv_path={report.dotenv_path}",
        f"dotenv_exists={report.dotenv_exists}",
        f"workspace_registry_path={workspace_registry_path}",
        f"workspace_registry_exists={workspace_registry_exists}",
        f"config_valid={report.config_valid}",
        f"codex_command={report.codex_command}",
        f"codex_command_found={report.codex_command_path is not None}",
        f"codex_command_path={codex_command_path}",
        f"default_agent_backend={report.default_agent_backend or ''}",
        f"default_workspace_id={report.default_workspace_id or ''}",
        f"default_workspace_path={default_workspace_path}",
        f"workspace_count={report.workspace_count if report.workspace_count is not None else ''}",
    ]
    if report.config_error is not None:
        lines.append(f"config_error={report.config_error}")
    if report.hint is not None:
        lines.append(f"hint={report.hint}")
    return "\n".join(lines)


def format_path_for_display(path: Path, base_dir: Path) -> str:
    """パスを表示用の相対形式へ整形する。

    Parameters
    ----------
    path : Path
        整形対象のパス。
    base_dir : Path
        相対化の基準ディレクトリ。

    Returns
    -------
    str
        表示用のパス文字列。
    """

    try:
        return str(path.relative_to(base_dir))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
