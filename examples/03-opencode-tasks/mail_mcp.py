"""Почтовый MCP на официальном SDK; только учебный Mailpit на loopback."""
from email.message import EmailMessage
import json
from pathlib import Path
import smtplib
import threading
from urllib.request import urlopen
from uuid import uuid4
from mcp.server.fastmcp import FastMCP
from check import hashes

ROOT = Path(__file__).resolve().parent
STATE = ROOT/'.lab/mail.json'
LOCK = threading.Lock()
RECIPIENT = 'boss@example.test'
mcp = FastMCP('Учебная почта', instructions='Подготовь черновик; отправляй только после отдельного подтверждения человека.')


def load_state():
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def save_state(state):
    STATE.parent.mkdir(exist_ok=True)
    temp = STATE.with_suffix('.tmp')
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2)+'\n')
    temp.replace(STATE)


def checked_report():
    path = ROOT/'.lab/checks.json'
    if not path.exists():
        raise ValueError('Сначала запустите python check.py')
    report = json.loads(path.read_text())
    if not report.get('passed') or report.get('source_hashes') != hashes():
        raise ValueError('Проверки не прошли или исходники изменились после проверки')
    return report


def mailbox_messages():
    # Адрес фиксирован; пользователь не может подставить другой URL или внешний SMTP.
    with urlopen('http://127.0.0.1:8025/api/v1/messages', timeout=5) as response:  # nosec B310
        return json.load(response).get('messages', [])


def find_message(message_id):
    for item in mailbox_messages():
        item_id = item['ID']
        if not isinstance(item_id, str) or not all(c.isalnum() or c == '-' for c in item_id):
            continue
        with urlopen('http://127.0.0.1:8025/api/v1/message/'+item_id, timeout=5) as response:  # nosec B310
            message = json.load(response)
        if message.get('MessageID', '').strip('<>') == message_id.strip('<>'):
            return {'mailpit_id': item_id, 'subject': message.get('Subject'), 'recipient': RECIPIENT}
    return None


@mcp.tool()
def prepare_report() -> dict:
    """Подготовить письмо Боссу по успешным актуальным проверкам; ничего не отправляет."""
    report = checked_report()
    draft_id = uuid4().hex
    draft = {'id': draft_id, 'to': RECIPIENT, 'subject': 'Учебная задача: отметка выполнена',
             'body': 'Реализовано завершение задачи по ID.\n'+
             '\n'.join(' '.join(row['command'])+': код '+str(row['exit_code']) for row in report['checks'])+
             '\nАвтоматические проверки пройдены. Ручная приёмка и ограничения описаны в review.md.\n'
             'Это учебное письмо, принятое локальным Mailpit; внешняя доставка не выполняется.',
             'message_id': f'<task-demo-{draft_id}@example.test>', 'status': 'draft',
             'source_hashes': report['source_hashes']}
    with LOCK:
        state = load_state()
        state[draft_id] = draft
        save_state(state)
    return draft


@mcp.tool()
def send_report(draft_id: str, confirmation: str) -> dict:
    """Отправить просмотренный черновик после разрешения человека; повтор не создаёт дубликат.

    confirmation должна быть точной фразой «Отправить Боссу». Это дополнительный шаг,
    а не доказательство согласия человека: инструмент в OpenCode настроен на ask.
    """
    if confirmation != 'Отправить Боссу':
        raise ValueError('Нужно отдельное подтверждение после просмотра черновика')
    with LOCK:
        state = load_state()
        if draft_id not in state:
            raise ValueError('Черновик не найден')
        draft = state[draft_id]
        if draft['status'] != 'draft':
            existing = find_message(draft['message_id'])
            if existing:
                return {'status': 'already_received_locally', **existing}
            raise ValueError('Исход отправки неизвестен; проверьте Mailpit, автоматически не повторяем')
        report = checked_report()
        if draft['source_hashes'] != report['source_hashes']:
            raise ValueError('После подготовки письма изменились исходники')
        message = EmailMessage()
        message['From'] = 'lector@example.test'
        message['To'] = RECIPIENT
        message['Subject'] = draft['subject']
        message['Message-ID'] = draft['message_id']
        message.set_content(draft['body'])
        draft['status'] = 'sending_or_unknown'
        save_state(state)
        # TCP-адрес и адресат зафиксированы для учебной среды; внешней доставки нет.
        with smtplib.SMTP('127.0.0.1', 1025, timeout=5) as smtp:
            smtp.send_message(message)
        found = find_message(draft['message_id'])
        if not found:
            raise ValueError('SMTP принял письмо, но появление в локальных входящих ещё не подтверждено')
        draft['status'] = 'received_locally'
        save_state(state)
        return {'status': 'received_locally', **found}


@mcp.tool()
def list_inbox() -> dict:
    """Показать учебные входящие Mailpit; не читает личную почту."""
    return {'messages': [{'id': m['ID'], 'subject': m['Subject']} for m in mailbox_messages()]}


if __name__ == '__main__':
    mcp.run(transport='stdio')
