from openai import AsyncOpenAI, OpenAI
from openai.types.chat import ChatCompletionChunk, ChatCompletionMessageParam, ChatCompletionUserMessageParam
from dotenv import load_dotenv
import sys
import os
import time
import sqlite3
from rich import print

from observable import Observable, Observer


load_dotenv('.env.local')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if not OPENAI_API_KEY:
    OPENAI_API_KEY = input('Enter your OpenAI API key: ')

settings = dict(
    model='gpt-3.5-turbo',
)

ai = OpenAI(api_key=OPENAI_API_KEY)
db = sqlite3.connect('data.db')


class State(Observable):
    def __init__(self):
        super().__init__()
        self.chat_id: int | None = None
        self._messages = []

    @property
    def messages(self):
        return self._messages

    def add_message(self, message: dict[str, str]):
        self._messages.append(message)
        self.notify_observers(message)

    def clear_messages(self):
        self._messages = []

    def new_chat(self):
        self.chat_id = insert_chat()

    def reset_chat(self):
        self.clear_messages()
        self.chat_id = None


class StateObserver(Observer):
    def update(self, observable: State, message: dict[str, str], *args, **kwargs):
        insert_message(message)


def create_tables():
    db.execute('''
        CREATE TABLE IF NOT EXISTS chat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at INTEGER,
            updated_at INTEGER
        )
    ''')
    db.execute('''
        CREATE TABLE IF NOT EXISTS message (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            role TEXT,
            content TEXT,
            created_at INTEGER,
            usage TEXT,
            FOREIGN KEY (chat_id) REFERENCES chat (id)
        )
    ''')
    db.commit()


def insert_message(message: dict[str, str]) -> int | None:
    cur = db.execute(
        'INSERT INTO message (chat_id, role, content, created_at, usage) VALUES (?, ?, ?, ?, ?)',
        (state.chat_id, message['role'], message['content'], int(time.time()), message.get('usage'))
    )
    db.commit()
    return cur.lastrowid


def insert_chat() -> int | None:
    cur = db.execute(
        'INSERT INTO chat (created_at) VALUES (?)',
        (int(time.time()),)
    )
    db.commit()
    return cur.lastrowid


state = State()
state.add_observer(StateObserver())


def create_prompt() -> dict[str, str]:
    print('[bold green]> [/]', end='')
    prompt = input()

    if prompt == 'quit':
        print('Goodbye!')
        sys.exit(0)
    elif prompt == 'clear':
        state.reset_chat()
        os.system('cls' if os.name == 'nt' else 'clear')
        return create_prompt()

    return {
        'role': 'user',
        'content': prompt
    }


def streaming_response() -> dict[str, str]:
    stream = ai.chat.completions.create(
        stream=True,
        model='gpt-3.5-turbo',
        messages=state.messages
    )

    response = {
        'role': 'assistant',
        'content': ''
    }

    print('\n🤖', end=' ')
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            print(chunk.choices[0].delta.content, end='', flush=True)
            response['content'] += chunk.choices[0].delta.content
    print('\n')

    return response


def main() -> None:

    create_tables()

    while 1:
        try:
            prompt = create_prompt()

            if state.chat_id is None:
                state.new_chat()

            state.add_message(prompt)
            response = streaming_response()
            state.add_message(response)
        except KeyboardInterrupt:
            db.close()
            print('\nGoodbye!')
            sys.exit(0)


if __name__ == "__main__":
    main()
