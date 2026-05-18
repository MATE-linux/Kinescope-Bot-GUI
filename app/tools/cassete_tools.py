import os


def load_messages_from_cassette(file_path):
    if not os.path.exists(file_path):
        return [
            "Это тестовое сообщение #1",
            "Это тестовое сообщение #2\nсо второй строкой",
            "#РАЗБАНЬМЕНЯ"
        ]
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    raw_messages = content.split('\n===\n')
    messages = [msg.strip() for msg in raw_messages if msg.strip()]
    if not messages:
        return [
            "Это тестовое сообщение #1",
            "Это тестовое сообщение #2\nсо второй строкой",
            "#РАЗБАНЬМЕНЯ"
        ]
    return messages