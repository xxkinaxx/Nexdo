"""Storage NEXDO: satu-satunya modul yang menyentuh file JSON.

Semua fitur (termasuk fitur developer lain) harus membaca/menyimpan data
lewat load_tasks() dan save_tasks(), bukan membuat penyimpanan sendiri.
"""

import json
import os
import tempfile
from pathlib import Path

# Lokasi file data: <root proyek>/data/tasks.json
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
TASKS_FILE = DATA_DIR / "tasks.json"


class StorageError(Exception):
    """Dilempar jika file JSON gagal dibaca atau ditulis."""


def _ensure_file_exists():
    """Buat folder data dan file tasks.json (berisi list kosong) jika belum ada."""
    try:
        TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not TASKS_FILE.exists():
            TASKS_FILE.write_text("[]", encoding="utf-8")
    except OSError as err:
        raise StorageError(f"Gagal menyiapkan file data: {err}") from err


def load_tasks():
    """Membaca seluruh tugas dari JSON.

    Returns:
        list[dict]: daftar tugas (list kosong jika file baru/kosong).

    Raises:
        StorageError: jika file tidak bisa dibaca atau isinya rusak.
            File yang rusak TIDAK diubah/ditimpa agar data bisa diperbaiki manual.
    """
    _ensure_file_exists()

    try:
        content = TASKS_FILE.read_text(encoding="utf-8")
    except OSError as err:
        raise StorageError(f"Gagal membaca file data: {err}") from err

    # File kosong -> mulai dengan daftar tugas kosong
    if not content.strip():
        return []

    try:
        data = json.loads(content)
    except json.JSONDecodeError as err:
        raise StorageError(
            f"Isi {TASKS_FILE.name} bukan JSON yang valid ({err}). "
            "File tidak diubah; perbaiki secara manual atau pulihkan dari backup."
        ) from err

    if not isinstance(data, list):
        raise StorageError(f"Isi {TASKS_FILE.name} harus berupa list of task.")

    return data


def save_tasks(tasks):
    """Menyimpan seluruh tugas ke JSON.

    Menulis ke file sementara dahulu lalu menggantinya (atomic), sehingga
    data lama tidak hilang jika proses penulisan gagal di tengah jalan.

    Args:
        tasks (list[dict]): daftar tugas yang akan disimpan.

    Returns:
        bool: True jika berhasil.

    Raises:
        ValueError: jika tasks bukan list.
        StorageError: jika penulisan gagal.
    """
    if not isinstance(tasks, list):
        raise ValueError("tasks harus berupa list.")

    tmp_name = None
    try:
        TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=TASKS_FILE.parent, prefix="tasks_", suffix=".tmp"
        )
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            json.dump(tasks, tmp_file, indent=4, ensure_ascii=False)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
        os.replace(tmp_name, TASKS_FILE)  # penggantian atomic
        return True
    except (OSError, TypeError) as err:
        # Bersihkan file sementara bila ada
        if tmp_name and os.path.exists(tmp_name):
            try:
                os.remove(tmp_name)
            except OSError:
                pass
        raise StorageError(f"Gagal menyimpan data: {err}") from err
