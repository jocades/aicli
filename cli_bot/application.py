from openai import AsyncOpenAI, OpenAI
from openai.types.chat import ChatCompletionChunk, ChatCompletionMessageParam, ChatCompletionUserMessageParam
from dotenv import load_dotenv
import sys
import os
import time
from pydantic import BaseModel
import sqlite3
from rich import print

from observable import Observable, Observer

settings = dict(
    model='gpt-3.5-turbo',
)


load_dotenv('.env.local')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if not OPENAI_API_KEY:
    OPENAI_API_KEY = input('Enter your OpenAI API key: ')


ai = OpenAI(api_key=OPENAI_API_KEY)


class Chat(BaseModel):
    id: int | None = None
    created_at: int
    updated_at: int | None = None


class Message(BaseModel):
    id: int | None = None
    chat_id: int
    role: str
    content: str
    created_at: int
    usage: str | None = None


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


class StateObserver(Observer):
    def update(self, observable: State, message: dict[str, str], *args, **kwargs):
        print('Inserting message...')
        insert_message(message)
        print('Message inserted!')


state = State()
state.add_observer(StateObserver())


def check_completion() -> None:
    completion = ai.chat.completions.create(
        model='gpt-3.5-turbo',
        messages=[
            {
                'role': 'user',
                'content': 'Say this is a test'
            }
        ],
    )
    print(completion.model_dump())

    completion.choices[0].message.content

    comp = {
        'id': 'chatcmpl-8UBwYbi0aZGyOtNB3WJMFz9o8ZSMb',
        'choices': [
            {
                'finish_reason': 'stop',
                'index': 0,
                'message': {
                    'content': '"This is a test."',
                    'role': 'assistant',
                    'function_call': None,
                    'tool_calls': None
                }
            }
        ],
        'created': 1702206442,
        'model': 'gpt-3.5-turbo-0613',
        'object': 'chat.completion',
        'system_fingerprint': None,
        'usage': {'completion_tokens': 5, 'prompt_tokens': 12, 'total_tokens': 17}
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

    print('🤖', end=' ')
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            print(chunk.choices[0].delta.content, end='', flush=True)
            response['content'] += chunk.choices[0].delta.content
    print('\n')

    return response


def create_prompt() -> dict[str, str]:
    prompt = input('> ')

    if prompt == 'quit':
        print('Goodbye!')
        sys.exit(0)
    elif prompt == 'clear':
        state.clear_messages()
        os.system('cls' if os.name == 'nt' else 'clear')
        return create_prompt()

    return {
        'role': 'user',
        'content': prompt
    }


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


def main() -> None:
    global db
    db = sqlite3.connect('data.db')

    create_tables()

    while 1:
        try:
            prompt = create_prompt()
            if state.chat_id is None:
                state.chat_id = insert_chat()
            state.add_message(prompt)
            print()
            response = streaming_response()
            state.add_message(response)

        except KeyboardInterrupt:
            db.close()
            print('\nGoodbye!')
            sys.exit(0)


if __name__ == "__main__":
    main()
