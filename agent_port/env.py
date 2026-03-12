"""環境変数と `.env` 読み込みを補助する。"""

from __future__ import annotations

import os
from pathlib import Path


def load_dotenv_file(base_dir: Path) -> None:
    """`.env` を読み込む。

    Parameters
    ----------
    base_dir : Path
        `.env` を探す基準ディレクトリ。

    Returns
    -------
    None
        未設定の環境変数だけを `.env` から補完する。
    """

    dotenv_path = base_dir / ".env"
    if not dotenv_path.exists():
        return

    for line in dotenv_path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue

        key, value = text.split("=", 1)
        name = key.strip()
        if not name:
            continue

        os.environ.setdefault(name, value.strip())


def read_optional_env(name: str) -> str | None:
    """任意の環境変数を読む。

    Parameters
    ----------
    name : str
        読み込む環境変数名。

    Returns
    -------
    str | None
        空文字を除いた値。未設定なら `None`。
    """

    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def read_positive_int_env(
    name: str,
    default: int,
    error_factory: type[Exception],
) -> int:
    """正の整数の環境変数を読む。

    Parameters
    ----------
    name : str
        読み込む環境変数名。
    default : int
        未設定時の既定値。
    error_factory : type[Exception]
        変換失敗時に使う例外型。

    Returns
    -------
    int
        読み込んだ整数値。
    """

    value = os.getenv(name)
    if value is None:
        return default

    try:
        number = int(value)
    except ValueError as exc:
        raise error_factory(f"{name} は整数で指定してください。") from exc

    if number < 1:
        raise error_factory(f"{name} は 1 以上で指定してください。")

    return number


def read_choice_env(
    name: str,
    default: str,
    allowed_values: set[str],
    error_factory: type[Exception],
) -> str:
    """候補の中から 1 つ選ぶ環境変数を読む。

    Parameters
    ----------
    name : str
        読み込む環境変数名。
    default : str
        未設定時の既定値。
    allowed_values : set[str]
        許可する値の集合。
    error_factory : type[Exception]
        検証失敗時に使う例外型。

    Returns
    -------
    str
        検証済みの値。
    """

    value = os.getenv(name, default).strip()
    if value not in allowed_values:
        choices = ", ".join(sorted(allowed_values))
        raise error_factory(f"{name} は {choices} のいずれかで指定してください。")
    return value
