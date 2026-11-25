"""NEXDO Task Manager - entry point dan menu CLI.

File ini hanya mengurus tampilan dan input pengguna.
Seluruh logika tugas ada di core/task_manager.py.
"""

from datetime import date

from core import task_manager as tm
from core.storage import StorageError

MENU = """
================================
        NEXDO TASK MANAGER
================================

[1] Add New Task
[2] View All Tasks
[3] View Task Details
[4] Edit Task
[5] Delete Task
[6] Search Task
[7] Update Task Status
[0] Exit
"""


# ---------------------------------------------------------------------------
# Helper input & tampilan
# ---------------------------------------------------------------------------

def prompt_valid(label, validator, default=None, allow_blank=False):
    """Meminta input sampai valid.

    - validator: fungsi yang me-return nilai bersih atau raise ValueError.
    - default: dipakai jika pengguna menekan Enter (None = tidak ada default).
    - allow_blank: jika True, Enter mengembalikan None (artinya "tidak diubah").
    """
    while True:
        raw = input(f"{label}: ").strip()
        if raw == "":
            if default is not None:
                return default
            if allow_blank:
                return None
        try:
            return validator(raw)
        except ValueError as err:
            print(f"  [!] {err}")


def choice_validator(options, validator):
    """Mengizinkan pengguna memilih lewat nomor (1, 2, 3) atau mengetik namanya."""
    def check(value):
        if value.isdigit() and 1 <= int(value) <= len(options):
            return options[int(value) - 1]
        return validator(value)
    return check


def deadline_validator(task_date):
    """Validator deadline yang juga memeriksa agar tidak lebih awal dari task_date."""
    def check(value):
        deadline = tm.validate_date(value)
        tm.validate_date_range(task_date, deadline)
        return deadline
    return check


def options_text(options):
    """Contoh: '1=High, 2=Medium, 3=Low'."""
    return ", ".join(f"{i}={name}" for i, name in enumerate(options, start=1))


def print_task_table(tasks):
    """Menampilkan daftar tugas dalam bentuk tabel sederhana."""
    header = f"{'ID':<4} {'Title':<28} {'Deadline':<11} {'Priority':<8} {'Status':<12} Category"
    print(header)
    print("-" * len(header))
    for task in tasks:
        title = task["title"] if len(task["title"]) <= 27 else task["title"][:24] + "..."
        print(f"{task['id']:<4} {title:<28} {task['deadline']:<11} "
              f"{task['priority']:<8} {task['status']:<12} {task['category']}")


def print_task_detail(task):
    """Menampilkan seluruh field satu tugas."""
    fields = [
        ("ID", "id"), ("Title", "title"), ("Description", "description"),
        ("Task Date", "task_date"), ("Deadline", "deadline"),
        ("Priority", "priority"), ("Category", "category"),
        ("Status", "status"), ("Created At", "created_at"),
    ]
    for label, key in fields:
        print(f"{label:<12}: {task.get(key, '')}")


# ---------------------------------------------------------------------------
# Handler tiap menu (hanya memanggil fungsi task_manager)
# ---------------------------------------------------------------------------

def menu_add_task():
    print("\n--- Add New Task ---")
    title = prompt_valid("Title", lambda v: tm.validate_text(v, "Judul"))
    description = prompt_valid("Description (boleh kosong)", str, default="")
    today = date.today().strftime(tm.DATE_FORMAT)
    task_date = prompt_valid(f"Task date YYYY-MM-DD (Enter = {today})",
                             tm.validate_date, default=today)
    deadline = prompt_valid("Deadline YYYY-MM-DD", deadline_validator(task_date))
    priority = prompt_valid(
        f"Priority [{options_text(tm.VALID_PRIORITIES)}] (Enter = Medium)",
        choice_validator(tm.VALID_PRIORITIES, tm.validate_priority), default="Medium")
    category = prompt_valid("Category (Enter = General)", str, default="General")

    task = tm.add_task(title, deadline, task_date=task_date, description=description,
                       priority=priority, category=category)
    print(f"\n[OK] Tugas berhasil ditambahkan dengan ID {task['id']}.")


def menu_view_all():
    print("\n--- All Tasks ---")
    tasks = tm.get_all_tasks()
    if not tasks:
        print("Belum ada tugas.")
        return
    print_task_table(tasks)


def menu_view_detail():
    print("\n--- Task Details ---")
    task_id = prompt_valid("Task ID", tm.validate_task_id)
    print()
    print_task_detail(tm.get_task_by_id(task_id))


def menu_edit_task():
    print("\n--- Edit Task ---")
    task_id = prompt_valid("Task ID", tm.validate_task_id)
    current = tm.get_task_by_id(task_id)
    print("\nTekan Enter untuk mempertahankan nilai lama.\n")

    title = prompt_valid(f"Title [{current['title']}]",
                         lambda v: tm.validate_text(v, "Judul"), allow_blank=True)
    description = prompt_valid(f"Description [{current['description']}]",
                               str, allow_blank=True)
    task_date = prompt_valid(f"Task date [{current['task_date']}]",
                             tm.validate_date, allow_blank=True)
    effective_date = task_date or current["task_date"]
    deadline = prompt_valid(f"Deadline [{current['deadline']}]",
                            deadline_validator(effective_date), allow_blank=True)
    priority = prompt_valid(
        f"Priority [{current['priority']}] ({options_text(tm.VALID_PRIORITIES)})",
        choice_validator(tm.VALID_PRIORITIES, tm.validate_priority), allow_blank=True)
    category = prompt_valid(f"Category [{current['category']}]", str, allow_blank=True)
    status = prompt_valid(
        f"Status [{current['status']}] ({options_text(tm.VALID_STATUSES)})",
        choice_validator(tm.VALID_STATUSES, tm.validate_status), allow_blank=True)

    tm.update_task(task_id, title=title, description=description, task_date=task_date,
                   deadline=deadline, priority=priority, category=category, status=status)
    print("\n[OK] Tugas berhasil diperbarui.")


def menu_delete_task():
    print("\n--- Delete Task ---")
    task_id = prompt_valid("Task ID", tm.validate_task_id)
    task = tm.get_task_by_id(task_id)
    confirm = input(f"Hapus '{task['title']}'? (y/n): ").strip().lower()
    if confirm == "y":
        tm.delete_task(task_id)
        print("[OK] Tugas berhasil dihapus.")
    else:
        print("Penghapusan dibatalkan.")


def menu_search_task():
    print("\n--- Search Task ---")
    keyword = prompt_valid("Keyword (ID atau judul)",
                           lambda v: tm.validate_text(v, "Kata kunci"))
    results = tm.search_tasks(keyword)
    if not results:
        print("Tidak ada tugas yang cocok.")
        return
    print(f"\nDitemukan {len(results)} tugas:\n")
    print_task_table(results)


def menu_update_status():
    print("\n--- Update Task Status ---")
    task_id = prompt_valid("Task ID", tm.validate_task_id)
    current = tm.get_task_by_id(task_id)
    print(f"Status saat ini: {current['status']}")
    status = prompt_valid(
        f"New status [{options_text(tm.VALID_STATUSES)}]",
        choice_validator(tm.VALID_STATUSES, tm.validate_status))
    tm.update_task_status(task_id, status)
    print("[OK] Status berhasil diperbarui.")


ACTIONS = {
    "1": menu_add_task,
    "2": menu_view_all,
    "3": menu_view_detail,
    "4": menu_edit_task,
    "5": menu_delete_task,
    "6": menu_search_task,
    "7": menu_update_status,
}


# ---------------------------------------------------------------------------
# Program utama
# ---------------------------------------------------------------------------

def main():
    while True:
        print(MENU)
        choice = input("Select menu: ").strip()

        if choice == "0":
            print("Terima kasih telah menggunakan NEXDO. Sampai jumpa!")
            break

        action = ACTIONS.get(choice)
        if action is None:
            print("[!] Menu tidak valid. Pilih angka 0-7.")
            continue

        try:
            action()
        except (ValueError, tm.TaskNotFoundError, StorageError) as err:
            print(f"\n[ERROR] {err}")

        input("\nTekan Enter untuk kembali ke menu...")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nProgram dihentikan.")
