"""workspace 読み込みを確認する。"""

from pathlib import Path

import pytest

from agent_port.workspaces import (
    WorkspaceRegistryError,
    load_workspace_registry_from_json,
)


def test_load_workspace_registry_reads_items(tmp_path: Path) -> None:
    """JSON から workspace を読めることを確認する。

    Parameters
    ----------
    tmp_path : Path
        テスト用ディレクトリ。

    Returns
    -------
    None
        path と allowed_agents が読み込まれることを確認する。
    """

    external_root = tmp_path.parent / "registry-workspace"
    external_root.mkdir()
    registry_path = tmp_path / "workspaces.json"
    registry_path.write_text(
        (
            '{"workspaces":['
            f'{{"id":"sample","path":"{external_root.as_posix()}","allowed_agents":["codex"]}}'
            "]} "
        ).strip(),
        encoding="utf-8",
    )

    registry = load_workspace_registry_from_json(
        registry_path=registry_path,
        control_root=tmp_path,
    )

    workspace = registry.get_workspace("sample")
    assert workspace.path == external_root.resolve()
    assert workspace.supports_agent("codex") is True
    assert workspace.supports_agent("claude_code") is False


def test_load_workspace_registry_rejects_control_root_child(tmp_path: Path) -> None:
    """本体配下の workspace を拒否することを確認する。

    Parameters
    ----------
    tmp_path : Path
        テスト用ディレクトリ。

    Returns
    -------
    None
        control root 配下を指定すると例外になることを確認する。
    """

    internal_root = tmp_path / "workspace"
    internal_root.mkdir()
    registry_path = tmp_path / "workspaces.json"
    registry_path.write_text(
        (
            '{"workspaces":['
            f'{{"id":"sample","path":"{internal_root.as_posix()}"}}'
            "]} "
        ).strip(),
        encoding="utf-8",
    )

    with pytest.raises(WorkspaceRegistryError):
        load_workspace_registry_from_json(
            registry_path=registry_path,
            control_root=tmp_path,
        )
