"""環境変数と `.env` 読み込みを補助するモジュール。"""

from __future__ import annotations

from pathlib import Path
import os


def load_dotenv_file(base_dir: Path) -> None:
    """`.env` を読み込む。

    Parameters
    ----------
    base_dir : Path
        `.env` を探す基準ディレクトリ。

    Returns
    -------
    None
        未設定の環境変数だけを `.env` から補う。
    """

    dotenv_path = base_dir / ".env"
    if not dotenv_path.exists():
        return

    for line in dotenv_path.read_text(encoding="utf-8").splitlines():
        normalized_line = line.strip()
        if not normalized_line or normalized_line.startswith("#"):
            continue
        if "=" not in normalized_line:
            continue

        key, value = normalized_line.split("=", 1)
        env_name = key.strip()
        if not env_name:
            continue

        os.environ.setdefault(env_name, value.strip())


def read_optional_env(name: str) -> str | None:
    """環境変数を空白除去して読み込む。

    Parameters
    ----------
    name : str
        読み込む環境変数名。

    Returns
    -------
    str | None
        値があれば空白除去後の文字列、空なら `None`。
    """

    value = os.getenv(name)
    if value is None:
        return None
    stripped_value = value.strip()
    return stripped_value or None


def read_positive_int_env(
    name: str,
    default: int,
    error_factory: type[Exception],
) -> int:
    """正の整数環境変数を読み込む。

    Parameters
    ----------
    name : str
        読み込む環境変数名。
    default : int
        未設定時の既定値。
    error_factory : type[Exception]
        変換失敗時に送出する例外型。

    Returns
    -------
    int
        読み込んだ整数値。
    """

    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        parsed_value = int(raw_value)
    except ValueError as exc:
        raise error_factory(f"{name} は整数で指定してください。") from exc

    if parsed_value < 1:
        raise error_factory(f"{name} は 1 以上で指定してください。")

    return parsed_value


def read_choice_env(
    name: str,
    default: str,
    allowed_values: set[str],
    error_factory: type[Exception],
) -> str:
    """候補内の値だけ許可する環境変数を読み込む。

    Parameters
    ----------
    name : str
        読み込む環境変数名。
    default : str
        未設定時の既定値。
    allowed_values : set[str]
        許可する値一覧。
    error_factory : type[Exception]
        検証失敗時に送出する例外型。

    Returns
    -------
    str
        許可された値。
    """

    raw_value = os.getenv(name, default).strip()
    if raw_value not in allowed_values:
        allowed_values_text = ", ".join(sorted(allowed_values))
        raise error_factory(
            f"{name} は {allowed_values_text} のいずれかで指定してください。"
        )

    return raw_value
