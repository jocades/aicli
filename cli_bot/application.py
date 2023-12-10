import asyncio
from openai import AsyncOpenAI, OpenAI
from openai.types.chat import ChatCompletionMessageParam
from dotenv import load_dotenv
import sys
import os
import sqlite3
import time


# message table
sql_message_table = """CREATE TABLE IF NOT EXISTS message (
    id integer PRIMARY KEY,
    role text NOT NULL,
    content text NOT NULL
    settings text NOT NULL
);"""


load_dotenv('.env.local')

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if not OPENAI_API_KEY:
    OPENAI_API_KEY = input('Enter your OpenAI API key: ')

async_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

messages = []

client = OpenAI(api_key=OPENAI_API_KEY)


async def check_comp() -> None:
    completion = await async_client.chat.completions.create(
        model='gpt-3.5-turbo',
        messages=[
            {
                'role': 'user',
                'content': 'Say this is a test'
            }
        ],
    )
    print(completion.model_dump())

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


async def streaming_response(prompt: str) -> None:
    messages.append({
        'role': 'user',
        'content': prompt
    })

    print('MESSAGES', messages)

    stream = await async_client.chat.completions.create(
        stream=True,
        model='gpt-3.5-turbo',
        messages=messages
    )

    response = {
        'role': 'assistant',
        'content': ''
    }

    async for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            print(chunk.choices[0].delta.content, end='', flush=True)
            response['content'] += chunk.choices[0].delta.content

    print()
    messages.append(response)


def create_prompt() -> dict[str, str]:
    prompt = input('> ')
    return {
        'role': 'user',
        'content': prompt
    }


def sync_response(prompt: str) -> None:
    messages.append({
        'role': 'user',
        'content': prompt
    })

    print('MESSAGES', messages)

    stream = client.chat.completions.create(
        stream=True,
        model='gpt-3.5-turbo',
        messages=messages
    )

    response = {
        'role': 'assistant',
        'content': ''
    }

    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            print(chunk.choices[0].delta.content, end='', flush=True)
            response['content'] += chunk.choices[0].delta.content

    print()
    messages.append(response)


async def main() -> None:
    while 1:
        try:
            prompt = input('> ')
            await streaming_response(prompt)
        except KeyboardInterrupt:
            print('\nGoodbye!')
            sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
