"""Task Manager NEXDO: seluruh logika pengelolaan tugas.

Aturan return value (konsisten untuk semua fungsi publik):
- Fungsi yang mengembalikan satu tugas -> dict tugas.
- Fungsi yang mengembalikan banyak tugas -> list of dict (bisa kosong).
- Kesalahan TIDAK dikembalikan sebagai nilai khusus, tetapi dilempar sebagai:
    ValueError        : input tidak valid (format tanggal, priority, dll.)
    TaskNotFoundError : ID tugas tidak ditemukan
    StorageError      : gagal membaca/menulis file JSON

Modul ini tidak memakai input()/print() sehingga aman diimpor oleh modul lain.
"""

from datetime import date, datetime

from . import storage
from .storage import StorageError  # di-export ulang agar mudah di-import

DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

VALID_PRIORITIES = ("High", "Medium", "Low")
VALID_STATUSES = ("Pending", "In Progress", "Completed")


class TaskNotFoundError(LookupError):
    """Dilempar jika tugas dengan ID tertentu tidak ada."""


# ---------------------------------------------------------------------------
# Validasi (publik, boleh dipakai modul lain termasuk CLI)
# ---------------------------------------------------------------------------

def validate_text(value, label="Teks", required=True):
    """Membersihkan spasi berlebih dan memastikan teks tidak kosong jika required."""
    if value is None:
        value = ""
    text = str(value).strip()
    if required and not text:
        raise ValueError(f"{label} tidak boleh kosong.")
    return text


def validate_date(value):
    """Memvalidasi tanggal berformat YYYY-MM-DD. Return string yang sudah dinormalisasi."""
    try:
        parsed = datetime.strptime(str(value).strip(), DATE_FORMAT)
    except ValueError:
        raise ValueError(
            "Format tanggal harus YYYY-MM-DD dan tanggalnya valid (contoh: 2026-11-24)."
        ) from None
    return parsed.strftime(DATE_FORMAT)


def validate_date_range(task_date, deadline):
    """Deadline tidak boleh lebih awal dari task_date (keduanya format YYYY-MM-DD)."""
    if deadline < task_date:  # format YYYY-MM-DD aman dibandingkan sebagai string
        raise ValueError("Deadline tidak boleh lebih awal dari tanggal pengerjaan.")


def _validate_choice(value, options, label):
    """Mencocokkan pilihan tanpa peduli huruf besar/kecil. Return penulisan resmi."""
    cleaned = " ".join(str(value).split()).lower()
    for option in options:
        if option.lower() == cleaned:
            return option
    raise ValueError(f"{label} harus salah satu dari: {', '.join(options)}.")


def validate_priority(value):
    """Memastikan priority adalah High, Medium, atau Low."""
    return _validate_choice(value, VALID_PRIORITIES, "Priority")


def validate_status(value):
    """Memastikan status adalah Pending, In Progress, atau Completed."""
    return _validate_choice(value, VALID_STATUSES, "Status")


def validate_task_id(task_id):
    """Mengubah ID (int atau string angka) menjadi int. Raise ValueError jika tidak valid."""
    if isinstance(task_id, bool):
        raise ValueError("ID tugas harus berupa angka.")
    try:
        return int(str(task_id).strip())
    except ValueError:
        raise ValueError("ID tugas harus berupa angka.") from None


# ---------------------------------------------------------------------------
# Fungsi bantu internal
# ---------------------------------------------------------------------------

def _generate_id(tasks):
    """ID baru = ID terbesar yang ada + 1, sehingga tidak bertabrakan."""
    return max((task.get("id", 0) for task in tasks), default=0) + 1


def _find_index(tasks, task_id):
    """Mencari posisi tugas di list. Raise TaskNotFoundError jika tidak ada."""
    for index, task in enumerate(tasks):
        if task.get("id") == task_id:
            return index
    raise TaskNotFoundError(f"Tugas dengan ID {task_id} tidak ditemukan.")


# ---------------------------------------------------------------------------
# Fungsi inti (API untuk developer lain)
# ---------------------------------------------------------------------------

def add_task(title, deadline, task_date=None, description="",
             priority="Medium", category="General", status="Pending"):
    """Menambahkan tugas baru dan menyimpannya ke JSON.

    Args:
        title (str): judul tugas (wajib).
        deadline (str): batas akhir, format YYYY-MM-DD (wajib).
        task_date (str | None): tanggal rencana pengerjaan; default hari ini.
        description (str): deskripsi tugas.
        priority (str): High / Medium / Low.
        category (str): kategori bebas; default "General".
        status (str): Pending / In Progress / Completed.

    Returns:
        dict: tugas yang baru dibuat (lengkap dengan id dan created_at).
    """
    title = validate_text(title, "Judul")
    description = validate_text(description, "Deskripsi", required=False)
    category = validate_text(category, "Kategori", required=False) or "General"
    priority = validate_priority(priority)
    status = validate_status(status)
    deadline = validate_date(deadline)
    task_date = (validate_date(task_date) if task_date
                 else date.today().strftime(DATE_FORMAT))
    validate_date_range(task_date, deadline)

    tasks = storage.load_tasks()
    new_task = {
        "id": _generate_id(tasks),
        "title": title,
        "description": description,
        "task_date": task_date,
        "deadline": deadline,
        "priority": priority,
        "category": category,
        "status": status,
        "created_at": datetime.now().strftime(DATETIME_FORMAT),
    }
    tasks.append(new_task)
    storage.save_tasks(tasks)
    return new_task


def get_all_tasks():
    """Mengambil seluruh tugas.

    Returns:
        list[dict]: semua tugas (list kosong jika belum ada).
        Gunakan fungsi ini sebagai sumber data untuk fitur tambahan.
    """
    return storage.load_tasks()


def get_task_by_id(task_id):
    """Mengambil satu tugas berdasarkan ID.

    Returns:
        dict: tugas yang dicari.

    Raises:
        ValueError: ID bukan angka.
        TaskNotFoundError: ID tidak ditemukan.
    """
    task_id = validate_task_id(task_id)
    tasks = storage.load_tasks()
    return tasks[_find_index(tasks, task_id)]


def update_task(task_id, title=None, description=None, task_date=None,
                deadline=None, priority=None, category=None, status=None):
    """Mengubah tugas. Field yang bernilai None tidak diubah (tetap memakai data lama).

    ID dan created_at tidak dapat diubah.

    Returns:
        dict: tugas setelah diperbarui.

    Raises:
        ValueError: data baru tidak valid (tugas tidak disimpan).
        TaskNotFoundError: ID tidak ditemukan.
    """
    task_id = validate_task_id(task_id)
    tasks = storage.load_tasks()
    index = _find_index(tasks, task_id)

    updated = dict(tasks[index])  # salinan; tugas asli tidak berubah bila validasi gagal

    if title is not None:
        updated["title"] = validate_text(title, "Judul")
    if description is not None:
        updated["description"] = validate_text(description, "Deskripsi", required=False)
    if task_date is not None:
        updated["task_date"] = validate_date(task_date)
    if deadline is not None:
        updated["deadline"] = validate_date(deadline)
    if priority is not None:
        updated["priority"] = validate_priority(priority)
    if category is not None:
        updated["category"] = validate_text(category, "Kategori", required=False) or "General"
    if status is not None:
        updated["status"] = validate_status(status)

    validate_date_range(updated["task_date"], updated["deadline"])

    tasks[index] = updated
    storage.save_tasks(tasks)
    return updated


def delete_task(task_id):
    """Menghapus tugas berdasarkan ID.

    Returns:
        dict: tugas yang baru dihapus.

    Raises:
        ValueError: ID bukan angka.
        TaskNotFoundError: ID tidak ditemukan.
    """
    task_id = validate_task_id(task_id)
    tasks = storage.load_tasks()
    index = _find_index(tasks, task_id)
    removed = tasks.pop(index)
    storage.save_tasks(tasks)
    return removed


def search_tasks(keyword):
    """Mencari tugas berdasarkan ID atau kata kunci pada judul (tanpa peduli huruf besar/kecil).

    Returns:
        list[dict]: tugas yang cocok (list kosong jika tidak ada).

    Raises:
        ValueError: keyword kosong.
    """
    keyword = validate_text(keyword, "Kata kunci").lower()
    results = []
    for task in storage.load_tasks():
        matches_id = keyword == str(task.get("id"))
        matches_title = keyword in task.get("title", "").lower()
        if matches_id or matches_title:
            results.append(task)
    return results


def update_task_status(task_id, status):
    """Mengubah status tugas (Pending / In Progress / Completed).

    Returns:
        dict: tugas setelah statusnya diperbarui.
    """
    return update_task(task_id, status=status)
