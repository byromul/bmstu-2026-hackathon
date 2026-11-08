"""Приёмка поведения по спецификации, включая ID, отличающиеся от индексов."""
import copy
import tempfile
from pathlib import Path
import unittest
from app import page
from tasks import Store, complete_task


class TaskChecks(unittest.TestCase):
    def setUp(self):
        self.tasks = [{'id': 7, 'title': 'Первая', 'done': False},
                      {'id': 42, 'title': 'Вторая', 'done': False}]

    def test_selected_id_changes_and_other_does_not(self):
        complete_task(self.tasks, 42)
        self.assertEqual([t['done'] for t in self.tasks], [False, True])

    def test_id_one_is_not_index_one(self):
        items = [{'id': 1, 'done': False}, {'id': 2, 'done': False}]
        complete_task(items, 1)
        self.assertEqual([t['done'] for t in items], [True, False])

    def test_unknown_id_does_not_change_data(self):
        before = copy.deepcopy(self.tasks)
        for unknown_id in [0, 99]:
            with self.assertRaises(KeyError):
                complete_task(self.tasks, unknown_id)
        self.assertEqual(self.tasks, before)

    def test_repeated_completion_is_safe(self):
        complete_task(self.tasks, 42)
        before = copy.deepcopy(self.tasks)
        complete_task(self.tasks, 42)
        self.assertEqual(self.tasks, before)

    def test_invalid_id_is_rejected_without_changes(self):
        before = copy.deepcopy(self.tasks)
        for value in [True, '42', None]:
            with self.assertRaises(ValueError):
                complete_task(self.tasks, value)
        self.assertEqual(self.tasks, before)

    def test_change_survives_reopening_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'tasks.json'
            store = Store(path)
            store.complete(1)
            self.assertTrue(Store(path).load()[0]['done'])
            self.assertFalse(Store(path).load()[1]['done'])

    def test_unknown_id_does_not_rewrite_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'tasks.json'
            store = Store(path)
            before = path.read_bytes()
            with self.assertRaises(KeyError):
                store.complete(999)
            self.assertEqual(path.read_bytes(), before)

    def test_task_title_is_escaped_in_html(self):
        rendered = page([{'id': 1, 'title': '<script>alert(1)</script>', 'done': False}])
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', rendered)
        self.assertNotIn('<script>alert(1)</script>', rendered)


if __name__ == '__main__':
    unittest.main()
