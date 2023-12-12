import os
import io
import sys
import time
import sqlite3
import base64
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletionAssistantMessageParam,  ChatCompletionMessageParam, ChatCompletionUserMessageParam
from PIL import Image
from openai.types.chat.completion_create_params import ResponseFormat
from rich import print
from rich.status import Status

from .settings import settings, chat_settings


load_dotenv('.env.local')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if not OPENAI_API_KEY:
    OPENAI_API_KEY = input('Enter your OpenAI API key: ')


ai = OpenAI(api_key=OPENAI_API_KEY)
db = sqlite3.connect('data.db')


class State:
    def __init__(self):
        self.__mode: Literal['chat', 'image'] = 'chat'
        self.__chat_id: int | None = None
        self.__messages: list[ChatCompletionMessageParam] = []

    @property
    def mode(self):
        return self.__mode

    @mode.setter
    def mode(self, value: Literal['chat', 'image']):
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
    chat = 'chat'
    image = 'image'
    settings = 'settings'
    set = 'set'
    clear = 'clear'
    quit = 'quit'
    help = 'help'


def handle_action(prompt: str):
    if not prompt.startswith(settings.action_prefix):
        return

    action, *args = prompt[1:].split()

    if action not in Action.__dict__.keys():
        print(f'[red]- Invalid command[/] "{prompt}" (type "help" to see a list of available commands)\n')
        return new_prompt()

    if action == Action.set:
        if len(args) != 2:
            # tell the user to use the correct forma set needs 2 args
            print(f'[red]- Invalid command[/] "{prompt}" (set needs 2 arguments)\n')
            return new_prompt()

        setting, value = args

        if setting not in chat_settings.__dict__.keys():
            print(f'[red]- Invalid setting[/] "{setting}" (type "chat_settings" to see a list of available settings)\n')
            return new_prompt()

        try:
            setattr(chat_settings, setting, value)
            print(f'\n- [bold green]{setting.capitalize()}[/] set to [bold blue]{value}[/]\n')
            return new_prompt()
        except ValueError as e:
            print(f'\n[red]- Invalid value[/] "{value}", {e}\n')
            return new_prompt()

    if action == Action.quit:
        print('Goodbye!')
        sys.exit(0)
    elif action == Action.clear:
        state.reset_chat()
        os.system('cls' if os.name == 'nt' else 'clear')
        return new_prompt()
    elif action == Action.help:
        show_help()
        return new_prompt()
    elif action == Action.chat:
        if state.mode == 'chat':
            print('[red]- Chat mode is already active[/] (type "clear" to reset and start a new chat)\n')
            return new_prompt()
        state.mode = 'chat'
        print('[bold green]- MODE:[/] [bold blue]chat[/]\n')
        return new_prompt()
    elif action == Action.image:
        if state.mode == 'image':
            print('[bold red]Image mode is already active[/]\n')
            return new_prompt()
        state.mode = 'image'

        print('\n[bold green]- MODE:[/] [bold blue]image[/]\n')

        print('Enter a prompt to generate an image. For example:')
        example = 'A white siamese cat with bright green eyes, sitting on a red pillow'
        print(f'[dim]{example}[/]\n')

        return new_prompt()
    elif action == Action.settings:
        if state.mode == 'chat':
            print('\n[bold green]- Chat Settings:')
            for k, v in chat_settings.__dict__.items():
                print(f'\t- {k}: [bold blue]{v}[/]')
            print()
            return new_prompt()
        elif state.mode == 'image':
            print('\n[bold green]- Image Settings:')
            print('TODO')
            return new_prompt()


def new_prompt() -> ChatCompletionUserMessageParam:
    print('[bold green]> [/]', end='')
    prompt = input().strip()

    if not prompt:
        return new_prompt()

    handle_action(prompt)

    return {
        'role': 'user',
        'content': prompt
    }


def show_help() -> None:
    print('\n- Available commands:')
    for action in Action.__dict__.keys():
        if not action.startswith('__'):
            print(f'\t- [bold blue]{action}[/]')
    print()


def streaming_response() -> ChatCompletionAssistantMessageParam:
    print()
    with Status('[bold blue]Thinking...[/]'):
        stream = ai.chat.completions.create(
            stream=True,
            model=chat_settings.model,
            messages=state.messages
        )

    content = ''

    print('🤖', end=' ')
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            print(chunk.choices[0].delta.content, end='', flush=True)
            content += chunk.choices[0].delta.content
    print('\n')

    return {
        'role': 'assistant',
        'content': content,
    }


def generate_image(prompt: ChatCompletionUserMessageParam) -> None:
    content = str(prompt['content'])
    file_name = f'{content[0:len(content) // 2].replace(' ', '_')}_{int(time.time())}.png'

    output = Path('output')

    with Status('[bold blue]Generating image...[/]'):
        response = ai.images.generate(
            model='dall-e-3',
            prompt=content,
            size='1024x1024',
            n=1,
            response_format='b64_json',
        )

    img = response.data[0]
    if img.b64_json is None:
        raise Exception('Could not generate image')

    data = base64.b64decode(img.b64_json)

    output.mkdir(parents=True, exist_ok=True)
    (output / file_name).write_bytes(data)

    print(f'- [bold green]Image saved to[/] [bold blue]{output / file_name}[/]')

    Image.open(io.BytesIO(data)).show()


def chat_repl(prompt: ChatCompletionUserMessageParam) -> None:
    if state.chat_id is None:
        state.new_chat()

    state.add_message(prompt)
    response = streaming_response()
    state.add_message(response)


def repl() -> None:
    while 1:
        try:
            prompt = new_prompt()

            if state.mode == 'chat':
                chat_repl(prompt)
                continue

            if state.mode == 'image':
                generate_image(prompt)
                continue

        except KeyboardInterrupt:
            db.close()
            print('\nGoodbye!')
            sys.exit(0)


def main() -> None:
    create_tables()

    print('\nWelcome to the AI Playground!\n')
    print('Type "help" to see a list of available commands.')
    print('Type "quit" or press "Ctrl+C" to exit.\n')
    print('Or just ask me me anything you want!\n')

    repl()
