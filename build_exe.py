from __future__ import annotations

import argparse
import os
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path


APP_EXE_NAME = "Web_panel_by_ZigZiger"
PORTABLE_DIR_NAME = "Web_panel_by_ZigZiger_portable"


README_TEXT = """Web панель by ZigZiger
========================

Что это:
- Локальная панель для OBS, персонажа и Twitch-чата.
- Python на чужом ПК не нужен: достаточно запустить exe.

Как запустить:
1. Дважды нажми на Web_panel_by_ZigZiger.exe
2. Программа откроет панель в браузере
3. После запуска она останется доступна через системный трей

Как добавить в OBS:
1. Открой панель
2. Скопируй URL сцены из панели
3. Добавь его в OBS как Browser Source
4. Если нужен отдельный чат, так же добавь chat URL вторым Browser Source

Как настроить микрофон:
1. Открой блок "Микрофон и чувствительность"
2. Нажми "Обновить"
3. Выбери устройство
4. Нажми "Старт"
5. Подстрой "Порог речи" по уровню голоса

Что вставлять в поле чата:
- @имя_канала
- twitch.tv/имя_канала
- полную ссылку на канал Twitch
- ссылку на popout или embed чат

Как закрыть:
- Нажми правой кнопкой по иконке в трее
- Выбери "Закрыть"

Что важно:
- Настройки хранятся отдельно для каждого пользователя в %LOCALAPPDATA%\\mopsyan_sysan
- Если нужно полностью сбросить программу, закрой ее и удали эту папку
- Если порт 8765 занят, приложение выберет другой свободный порт
"""


def sha256_of(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_release_bundle(root: Path, exe_path: Path) -> tuple[Path, Path, Path]:
    release_root = root / "release"
    portable_dir = release_root / PORTABLE_DIR_NAME
    archive_base = release_root / PORTABLE_DIR_NAME
    archive_path = archive_base.with_suffix(".zip")
    readme_path = portable_dir / "README_RU.txt"
    checksum_path = portable_dir / "SHA256.txt"

    if portable_dir.exists():
        shutil.rmtree(portable_dir)
    portable_dir.mkdir(parents=True, exist_ok=True)
    release_root.mkdir(parents=True, exist_ok=True)

    target_exe = portable_dir / exe_path.name
    shutil.copy2(exe_path, target_exe)
    readme_path.write_text(README_TEXT, encoding="utf-8")
    checksum_path.write_text(
        f"{sha256_of(target_exe)} *{target_exe.name}\n",
        encoding="utf-8",
    )

    if archive_path.exists():
        archive_path.unlink()
    shutil.make_archive(str(archive_base), "zip", portable_dir)

    return portable_dir, archive_path, checksum_path


def build_executable(root: Path) -> Path:
    path_sep = os.pathsep

    data_pairs = [
        (root / "web", "web"),
        (root / "assets", "assets"),
        (root / "1.png", "."),
        (root / "2.png", "."),
        (root / "3.png", "."),
        (root / "obs_chat_overlay.html", "."),
        (root / "z_icon.ico", "."),
        (root / "z_icon.png", "."),
    ]

    args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--onefile",
        "--name",
        APP_EXE_NAME,
        "--icon",
        str(root / "z_icon.ico"),
        "--collect-data",
        "_sounddevice_data",
    ]

    for source, target in data_pairs:
        args.extend(["--add-data", f"{source}{path_sep}{target}"])

    args.append(str(root / "mopsyan_sysan.py"))

    try:
        subprocess.run(args, cwd=root, check=True)
    except subprocess.CalledProcessError as error:
        output = root / "dist" / f"{APP_EXE_NAME}.exe"
        if output.exists():
            raise RuntimeError(
                "Не удалось пересобрать exe. Скорее всего, текущий файл запущен или заблокирован. "
                "Закрой приложение и повтори сборку, либо используй build_exe.py --package-only."
            ) from error
        raise

    return root / "dist" / f"{APP_EXE_NAME}.exe"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--package-only",
        action="store_true",
        help="Не пересобирать exe, а только собрать portable-пакет из готового dist файла.",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    output = root / "dist" / f"{APP_EXE_NAME}.exe"
    if args.package_only:
        if not output.exists():
            raise FileNotFoundError(f"Не найден exe для упаковки: {output}")
    else:
        output = build_executable(root)

    if not output.exists():
        raise FileNotFoundError(f"Не найден итоговый exe: {output}")

    portable_dir, archive_path, checksum_path = build_release_bundle(root, output)

    print(output)
    print(portable_dir)
    print(archive_path)
    print(checksum_path)


if __name__ == "__main__":
    main()
