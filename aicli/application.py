import os
import sys
import time
import sqlite3

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletionAssistantMessageParam,  ChatCompletionMessageParam, ChatCompletionUserMessageParam
from rich import print
from rich.status import Status


load_dotenv('.env.local')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if not OPENAI_API_KEY:
    OPENAI_API_KEY = input('Enter your OpenAI API key: ')


settings = dict(
    model='gpt-3.5-turbo',
)

ai = OpenAI(api_key=OPENAI_API_KEY)
db = sqlite3.connect('data.db')

MODES = ['chat', 'image']


class State:
    def __init__(self):
        self.__mode = 'chat'  # chat | image
        self.__chat_id: int | None = None
        self.__messages: list[ChatCompletionMessageParam] = []

    @property
    def mode(self):
        return self.__mode

    @mode.setter
    def mode(self, value):
        if value not in MODES:
            raise Exception(f'Invalid mode, expected {', '.join(f'"{mode}"' for mode in MODES)}, got "{value}"')
        self.__mode = value

    @property
    def chat_id(self):
        return self.__chat_id

    def new_chat(self):
        self.__chat_id = insert_chat()

    def reset_chat(self):
        self.__chat_id = None
        self.__messages = []

    @property
    def messages(self):
        return self.__messages

    def add_message(self, message: ChatCompletionMessageParam):
        self.__messages.append(message)
        insert_message(message)


state = State()


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


def insert_chat() -> int:
    cur = db.execute(
        'INSERT INTO chat (created_at) VALUES (?)',
        (int(time.time()),)
    )
    db.commit()

    if cur.lastrowid is None:
        raise Exception('Could not insert chat into database')

    return cur.lastrowid


def insert_message(message: ChatCompletionMessageParam) -> int:
    cur = db.execute(
        'INSERT INTO message (chat_id, role, content, created_at, usage) VALUES (?, ?, ?, ?, ?)',
        (state.chat_id, message['role'], message['content'], int(time.time()), message.get('usage'))
    )
    db.commit()

    if cur.lastrowid is None:
        raise Exception('Could not insert message into database')

    return cur.lastrowid


class Action:
    quit = 'quit'
    clear = 'clear'
    help = 'help'
    chat = 'chat'
    image = 'image'


def create_prompt() -> ChatCompletionUserMessageParam:
    print('[bold green]> [/]', end='')
    prompt = input()

    if prompt == Action.quit:
        print('Goodbye!')
        sys.exit(0)
    elif prompt == Action.clear:
        state.reset_chat()
        os.system('cls' if os.name == 'nt' else 'clear')
        return create_prompt()
    elif prompt == Action.help:
        print('Available commands:')
        for action in Action.__dict__.keys():
            if not action.startswith('__'):
                print(f'  {action}')
        return create_prompt()
    elif prompt == Action.chat:
        state.mode = 'chat'
        return create_prompt()
    elif prompt == Action.image:
        state.mode = 'image'
        return create_prompt()

    return {
        'role': 'user',
        'content': prompt
    }


def streaming_response() -> ChatCompletionAssistantMessageParam:
    print()
    with Status('[bold green]Thinking...[/]'):
        stream = ai.chat.completions.create(
            stream=True,
            model=settings['model'],
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

    return response  # type: ignore


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
