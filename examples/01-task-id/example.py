"""Учебная ошибка: идентификатор задачи ошибочно используется как индекс."""


def complete_task(tasks, task_id):
    tasks[task_id]["done"] = True


if __name__ == "__main__":
    tasks = [{"id": 1, "done": False}, {"id": 2, "done": False}]
    complete_task(tasks, 1)
    # Проверяем воспроизводимость именно показанного ошибочного поведения.
    assert tasks == [{"id": 1, "done": False}, {"id": 2, "done": True}]
    for task in tasks:
        state = "выполнена" if task["done"] else "не выполнена"
        print(f"ID {task['id']}: {state}")
