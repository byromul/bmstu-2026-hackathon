# Использование ИИ-агентов для быстрого программирования

Первый драфт: слайды 01–10 теоретического блока, около 12 минут. Продолжение теории и демонстрации ещё не подготовлены. Требования — в [SPEC.md](SPEC.md); сценарий — в [script.md](script.md).

## Блок 1. От выбора агента до проверенного результата

## Слайд 01. Использование ИИ-агентов для быстрого программирования

<!-- layout: cover; time: 00:00–00:40 -->

<div class="cover-meta">14 ноября 2026 · Лекция и демонстрация</div>
<div class="cover-subtitle">От задания до результата, который можно проверить</div>
<div class="cover-agenda"><span><b>40 минут</b>Принципы работы</span><span><b>40 минут</b>Разработка с агентом</span></div>

---

## Слайд 02. Завершилась другая задача

<!-- layout: code; time: 00:40–01:50 -->

Задание: отметить выполненной задачу с **ID 1**.

```python
tasks = [
    {"id": 1, "done": False},
    {"id": 2, "done": False},
]

def complete_task(tasks, task_id):
    tasks[task_id]["done"] = True

complete_task(tasks, 1)
```

<div class="code-result"><p class="label">Результат запуска</p><div class="result-row"><b>ID 1</b><span>не выполнена</span></div><div class="result-row wrong"><b>ID 2</b><span>выполнена</span></div><p class="small">Код завершился без ошибки.<br>Требование не выполнено.</p></div>

**ID задачи и позиция в списке могут не совпадать.**

Источники: [Python: последовательности](https://docs.python.org/3/library/stdtypes.html#common-sequence-operations) · [Воспроизводимый пример](examples/01-task-id/README.md)

---

## Слайд 03. Жизненный цикл разработки

<!-- layout: cycle; time: 01:50–03:00 -->

**SDLC** · Software Development Life Cycle

<div class="cycle" role="img" aria-label="Требования, проектирование, реализация, проверка, выпуск, эксплуатация и обратная связь. Затем новый цикл требований."><div class="cycle-node"><small>01</small><b>Требования</b><span>Что должно работать</span></div><div class="cycle-node"><small>02</small><b>Проектирование</b><span>Как это устроить</span></div><div class="cycle-node accent"><small>03</small><b>Реализация</b><span>Код и изменения</span></div><div class="cycle-node"><small>06</small><b>Эксплуатация</b><span>Обратная связь</span></div><div class="cycle-node"><small>05</small><b>Выпуск</b><span>Доступ пользователям</span></div><div class="cycle-node"><small>04</small><b>Проверка</b><span>Соответствие задаче</span></div><span class="edge e12" aria-hidden="true">→</span><span class="edge e23" aria-hidden="true">→</span><span class="edge e34" aria-hidden="true">↓</span><span class="edge e45" aria-hidden="true">←</span><span class="edge e56" aria-hidden="true">←</span><span class="edge e61" aria-hidden="true">↑</span></div>

Этапы могут пересекаться. Проверки и безопасность сопровождают весь цикл.

Источники: [AWS: SDLC](https://aws.amazon.com/what-is/sdlc/)

---

## Слайд 04. Как языковая модель получает ответ

<!-- layout: model; time: 03:00–04:00 -->

**LLM** · Large Language Model · большая языковая модель

<div class="model-rows"><div class="model-row"><p class="label">Обучение</p><div class="flow"><span>Примеры</span><i aria-hidden="true">→</i><span>Изменение параметров</span><i aria-hidden="true">→</i><strong>Обученная модель</strong></div></div><div class="model-row"><p class="label">Использование</p><div class="flow"><span>Контекст запроса</span><i aria-hidden="true">→</i><strong>Модель</strong><i aria-hidden="true">→</i><span>Следующий токен</span></div></div></div>

Токен может быть словом, его частью или знаком. Ответ складывается из последовательности токенов.

**Правдоподобный ответ может содержать ошибку.**

Источники: [AWS: большие языковые модели](https://aws.amazon.com/what-is/large-language-model/)

---

## Слайд 05. Что модель видит в текущем запросе

<!-- layout: context; time: 04:00–04:45 -->

<div class="context-map"><div class="context-history"><p class="label">История разговора</p><span>Задание</span><span>Уточнения</span><span>Предыдущие ответы</span><span class="muted">Более ранние сообщения</span></div><div class="context-choice"><b>Отбор<br>и сжатие</b><span aria-hidden="true">→</span></div><div class="context-window"><p class="label">Контекст одного запроса</p><span>Инструкции</span><span>Нужная часть истории</span><span>Файлы и результаты инструментов</span></div></div>

Приложение определяет, какую часть истории передать модели.

Источники: [Anthropic: управление контекстом](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents)

---

## Слайд 06. Ответ в чате и работа агента

<!-- layout: compare; time: 04:45–05:55 -->

<div class="compare-row"><h3>Чат без инструментов</h3><div class="flow"><span>Задание</span><i aria-hidden="true">→</i><span>Ответ с кодом</span><i aria-hidden="true">→</i><strong>Человек запускает</strong></div></div>
<div class="compare-row agent-row"><h3>Агент с инструментами</h3><div class="flow"><span>Задание</span><i aria-hidden="true">→</i><strong>Действие</strong><i aria-hidden="true">→</i><span>Результат</span></div><div class="return-path">Результат возвращается модели для следующего шага</div></div>

Прочитать файл · изменить код · запустить проверку

**Границы действий задаёт рабочая среда.**

Источники: [Anthropic: построение агентов](https://www.anthropic.com/engineering/building-effective-agents)

---

## Слайд 07. Harness организует работу агента

<!-- layout: harness; time: 05:55–07:00 -->

**Agent harness** («харнесс») · программная обвязка модели

<div class="harness-map"><div class="harness-context"><b>Контекст</b><span>Инструкции, история, результаты</span></div><div class="harness-core"><p class="label">Управляющий цикл</p><div class="flow"><strong>Модель</strong><i aria-hidden="true">→</i><span>Запрос действия</span><i aria-hidden="true">→</i><span>Проверка прав</span><i aria-hidden="true">→</i><span>Инструмент</span></div><div class="return-path">Результат инструмента возвращается в контекст</div></div><div class="harness-tools"><b>Инструменты</b><span>Файлы, команды, внешние сервисы</span></div></div>

Среда исполнения определяет, где действует агент и к чему у него есть доступ.

Источники: [Anthropic: harness, сессия и среда исполнения](https://www.anthropic.com/research/managed-agents)

---

## Слайд 08. Приложение, модель и провайдер

<!-- layout: layers; time: 07:00–08:10 -->

<div class="layers"><div class="layer"><span class="layer-num">01</span><div><h3>Приложение</h3><p>Интерфейс, цикл работы, инструменты и права</p></div><strong>OpenCode</strong></div><div class="layer"><span class="layer-num">02</span><div><h3>Модель</h3><p>Обрабатывает контекст и формирует ответ</p></div><strong>Выбираем отдельно</strong></div><div class="layer"><span class="layer-num">03</span><div><h3>Провайдер</h3><p>Предоставляет доступ, задаёт тариф и лимиты</p></div><strong>Выбираем отдельно</strong></div></div>

API: программный интерфейс для обращения приложения к сервису.

Источники: [OpenCode: подключение провайдеров](https://opencode.ai/docs/providers/)

---

## Слайд 09. Честный взгляд на доступ

<!-- layout: access; time: 08:10–10:00 -->

<div class="asof">Сведения на 8 ноября 2026</div>

| Сервис | Что учитывать |
| --- | --- |
| **Claude / Anthropic** | Нарушение региональных правил может привести к блокировке аккаунта |
| **OpenAI API** | Россия отсутствует в списке поддерживаемых стран |
| **Kimi / Moonshot AI** | 31 октября: Хабр сообщил о поддержке «Мир». 8 ноября: по проверке лектора способ недоступен |

Условия различаются между продуктами и меняются со временем.

Источники: [Anthropic: блокировки](https://www.anthropic.com/transparency/system-trust-reporting) · [OpenAI API: страны](https://developers.openai.com/api/docs/supported-countries) · [Kimi](https://www.kimi.com/) · [Хабр: сообщение об оплате](https://habr.com/ru/posts/1101976/)

---

## Слайд 10. Китайские модели для первого эксперимента

<!-- layout: options; time: 10:00–12:00 -->

| Семейство моделей | Разработчик / официальный сервис | Вариант работы |
| --- | --- | --- |
| **GLM** | Z.ai | Через API |
| **Kimi** | Moonshot AI | Kimi Code или API |
| **DeepSeek** | DeepSeek | Через API |

**Сравниваем на одной задаче с одинаковыми проверками.**

Качество результата · стоимость выполнения · контроль действий

Для агентского режима отдельно проверяем тариф, квоты и поддержку инструментов.

Источники: [Z.ai / GLM](https://z.ai/) · [Z.ai: API](https://docs.z.ai/guides/overview/quick-start) · [Kimi Code](https://www.kimi.com/code) · [Kimi API](https://www.kimi.ai/help/kimi-api/api-overview) · [DeepSeek: модели и API](https://api-docs.deepseek.com/quick_start/pricing/)

## Продолжение теории

Следующий фрагмент: посредники, vendor lock-in, постановка задачи и SDD. Далее — контекст, инструкции, расширения, безопасность и приёмка по [плану](SPEC.md#предлагаемый-план-на-80-минут). Концепция финала — в [спеке](SPEC.md#завершение-первой-части-своя-рабочая-среда).

## Блок 2. Рабочая сессия разработки в OpenCode

Каркас. Слайды демонстрации ещё не подготовлены; содержание задано в [плане демо](SPEC.md#блок-2-рабочая-сессия-разработки-в-opencode--40-минут).
