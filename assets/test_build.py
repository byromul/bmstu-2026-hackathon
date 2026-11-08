"""Проверки контракта Markdown → автономный HTML. Без сторонних библиотек."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build


def block(kind, data):
    return '```'+kind+'\n'+json.dumps(data, ensure_ascii=False)+'\n```\n'


class BuildChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'slides.md'
        self.notes = self.root / 'script.md'
        self.output = self.root / 'output.html'
        self.registry = self.root / 'ARTIFACTS.md'
        self.source.write_text('## Слайд 01. Пример\n\n'+block('slide', {'layout':'plain', 'time':'00:00–01:00'})+'\nТекст **слайда**.\n')
        self.notes.write_text('## Слайд 01. Пример\n\nТекст речи.\n')
        self.registry.write_text('# Артефакты\n')

    def append(self, text):
        with self.source.open('a') as stream:
            stream.write('\n'+text+'\n')

    def compile(self):
        with contextlib.redirect_stdout(io.StringIO()):
            build.build(self.source, self.notes, self.output, self.registry)
        return self.output.read_text()

    def image_fixture(self):
        (self.root/'prompt.md').write_text('Тестовый сохранённый промпт; генерация не выполнялась.')
        (self.root/'image.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        self.registry.write_text('| ART-0099 | [Промпт](prompt.md) | [Картинка](image.svg) | Фикстура | Тест | Нет |\n')

    def test_offline_build_is_repeatable(self):
        first = self.compile()
        self.assertEqual(first, self.compile())
        self.assertIn('<strong>слайда</strong>', first)
        self.assertNotIn('<script src=', first)
        self.assertNotIn('<link ', first)

    def test_mismatching_notes_rejected(self):
        self.notes.write_text('## Слайд 01. Другое название\n')
        with self.assertRaisesRegex(ValueError, 'различаются'):
            self.compile()
        self.assertFalse(self.output.exists())

    def test_duplicate_external_sources_rejected(self):
        self.append('Источники: [A](https://example.org) · [B](https://example.org)')
        with self.assertRaisesRegex(ValueError, 'Повтор ссылки'):
            self.compile()

    def test_local_document_links_are_text_in_deck_and_notes(self):
        self.append('[Пример](examples/example.py) [Спека](SPEC.md#section)')
        self.notes.write_text(self.notes.read_text()+'\n[Инструкция](README.md)\n')
        result = self.compile()
        self.assertNotIn('href="examples/', result)
        self.assertNotIn('href="SPEC.md', result)
        self.assertNotIn('href="README.md', result)
        self.assertIn('Пример Спека', result)
        self.assertIn('Инструкция', result)

    def test_artifact_image_embedded(self):
        self.image_fixture()
        self.append('![Описание](artifact:ART-0099)')
        result = self.compile()
        self.assertIn('src="data:image/svg+xml;base64,', result)
        self.assertIn('data-artifact="ART-0099"', result)
        self.assertNotIn('href="prompt.md', result)

    def test_missing_image_prompt_rejected(self):
        self.image_fixture()
        (self.root/'prompt.md').unlink()
        self.append('![Описание](artifact:ART-0099)')
        with self.assertRaisesRegex(ValueError, 'промпта'):
            self.compile()

    def test_unknown_artifact_rejected(self):
        self.append('![Описание](artifact:ART-0000)')
        with self.assertRaisesRegex(ValueError, 'одна запись'):
            self.compile()

    def test_direct_images_rejected(self):
        for image in ('https://example.org/image.png', 'assets/image.png'):
            with self.subTest(image=image), self.assertRaisesRegex(ValueError, 'artifact:'):
                build.markdown(f'![Описание]({image})', self.registry)

    def test_sources_cannot_be_overwritten(self):
        self.output = self.source
        original = self.source.read_text()
        with self.assertRaisesRegex(ValueError, 'перезаписывать'):
            self.compile()
        self.assertEqual(original, self.source.read_text())

    def test_invalid_timing_rejected(self):
        self.source.write_text(self.source.read_text().replace('00:00–01:00', '00:10–01:00'))
        with self.assertRaisesRegex(ValueError, 'тайминга'):
            self.compile()

    def test_code_escaped_but_html_rejected(self):
        self.append('```python\nprint("<script>")\n```')
        self.assertIn('&lt;script&gt;', self.compile())
        self.append('<div>Разметка</div>')
        with self.assertRaisesRegex(ValueError, 'HTML в Markdown'):
            self.compile()

    def test_author_instructions_not_on_screen(self):
        self.append(block('callout', {'text':'Главный вывод', 'tone':'warning', 'author':{'must':'СЕКРЕТ_ДИЗАЙНЕРА'}}))
        result = self.compile()
        self.assertNotIn('СЕКРЕТ_ДИЗАЙНЕРА', result)
        self.assertIn('callout-warning', result)

    def test_diagram_can_switch_renderer_without_changing_content(self):
        self.image_fixture()
        data = {'kind':'flows', 'rows':[{'title':'Цикл','nodes':[{'text':'Модель'},{'text':'Действие'}]}]}
        native = build.markdown(block('diagram', data), self.registry)
        self.assertIn('class="flow"', native)
        data.update(render='image', artifact='ART-0099', alt='Цикл')
        result = build.markdown(block('diagram', data), self.registry)
        self.assertIn('data-artifact="ART-0099"', result)
        self.assertNotIn('class="flow"', result)

    def test_table_dimensions_validated(self):
        self.append(block('table', {'columns':['A','B'], 'rows':[['1']]}))
        with self.assertRaisesRegex(ValueError, 'размеры'):
            self.compile()

    def test_unknown_directive_rejected(self):
        self.append(block('callout', {'text':'Вывод', 'colour':'red'}))
        with self.assertRaisesRegex(ValueError, 'Неизвестные поля'):
            self.compile()

    def test_notes_button_and_help_absent_hotkey_remains(self):
        result = self.compile()
        self.assertNotIn('id="toggle-notes"', result)
        self.assertNotIn('id="help"', result)
        self.assertIn("event.key.toLowerCase() === 'n'", result)

    def test_generated_html_rejects_local_navigation(self):
        with self.assertRaisesRegex(ValueError, 'Локальная ссылка'):
            build.ResourceCheck().feed('<a href="example.py">Код</a>')

    def test_mermaid_cannot_silently_become_source_code(self):
        with self.assertRaisesRegex(ValueError, 'Mermaid не подключён'):
            build.markdown('```mermaid\nflowchart LR\nA --> B\n```')

    def second_block(self):
        self.append('## Слайд 02. Практика\n\n'+block('slide', {'layout':'plain','time':'00:00–02:00','block':2})+'\nПрактический текст.\n')
        self.notes.write_text(self.notes.read_text()+'\n## Слайд 02. Практика\n\nРечь.\n')

    def test_second_block_has_independent_clock(self):
        self.second_block()
        result = self.compile()
        self.assertIn('data-block="2" data-seconds="120"', result)

    def test_selected_block_keeps_original_slide_id(self):
        self.second_block()
        build.build(self.source, self.notes, self.output, self.registry, selected_block=2)
        result = self.output.read_text()
        self.assertIn('id="slide-02"', result)
        self.assertNotIn('id="slide-01"', result)
        self.assertIn('slides.findIndex', result)

    def test_clock_cannot_reset_without_block_transition(self):
        self.second_block()
        self.source.write_text(self.source.read_text().replace('"block": 2', '"block": 1'))
        with self.assertRaisesRegex(ValueError, 'тайминга'):
            self.compile()


if __name__ == '__main__':
    unittest.main()
