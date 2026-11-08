"""Предметная логика учебного списка задач."""
import json
from pathlib import Path
import tempfile


def complete_task(tasks, task_id):
    """Отметить ровно одну задачу по ID; неизвестный ID не меняет список."""
    if type(task_id) is not int:
        raise ValueError('ID должен быть целым числом')
    for task in tasks:
        if task['id'] == task_id:
            task['done'] = True
            return task
    raise KeyError(task_id)


class Store:
    """Учебное хранение в JSON; HTTP-сервер обрабатывает запросы последовательно."""
    def __init__(self, path):
        self.path = Path(path)
        if not self.path.exists():
            self.save([
                {'id': 1, 'title': 'Подготовить задание агенту', 'done': False},
                {'id': 2, 'title': 'Проверить результат', 'done': False},
            ])

    def load(self):
        return json.loads(self.path.read_text(encoding='utf-8'))

    def save(self, tasks):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                         dir=self.path.parent, delete=False) as stream:
            temp = Path(stream.name)
            json.dump(tasks, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        try:
            temp.replace(self.path)
        finally:
            temp.unlink(missing_ok=True)

    def complete(self, task_id):
        tasks = self.load()
        result = complete_task(tasks, task_id)
        self.save(tasks)
        return result
