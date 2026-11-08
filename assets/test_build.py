"""Проверки автономного конвертера, без сторонних библиотек."""
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build


class BuildChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'slides.md'
        self.notes = self.root / 'script.md'
        self.output = self.root / 'output.html'
        self.source.write_text('## Слайд 01. Пример\n\n<!-- layout: model; time: 00:00–01:00 -->\n\nТекст **слайда**.\n')
        self.notes.write_text('## Слайд 01. Пример\n\nТекст речи.\n')

    def compile(self):
        with contextlib.redirect_stdout(io.StringIO()):
            build.build(self.source, self.notes, self.output)
        return self.output.read_text()

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
        with self.source.open('a') as f:
            f.write('\nИсточники: [A](https://example.org) · [B](https://example.org)\n')
        with self.assertRaisesRegex(ValueError, 'Повтор ссылки'):
            self.compile()

    def test_local_image_embedded_and_link_rebased(self):
        (self.root / 'diagram.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        (self.root / 'reference.md').write_text('# Материал')
        with self.source.open('a') as f:
            f.write('\n![Схема](diagram.svg)\n\n[Материал](reference.md)\n')
        self.output = self.root / 'out' / 'deck.html'
        result = self.compile()
        self.assertIn('src="data:image/svg+xml;base64,', result)
        self.assertTrue('href="../reference.md"' in result, 'Относительная ссылка должна вести на соседний исходный материал')

    def test_remote_image_rejected(self):
        with self.source.open('a') as f:
            f.write('\n![Схема](https://example.org/image.png)\n')
        with self.assertRaisesRegex(ValueError, 'локальным'):
            self.compile()

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

    def test_code_is_escaped(self):
        result = build.markdown('```python\nprint("<script>")\n```')
        self.assertIn('&lt;script&gt;', result)
        self.assertNotIn('<script>', result)


if __name__ == '__main__':
    unittest.main()
