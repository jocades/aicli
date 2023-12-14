class Settings:
    def __init__(self, temp=0.0, color='black'):
        self.temp = temp
        self.color = color


settings = Settings()


class Command:
    def set(self, setting, value):
        setattr(settings, setting, value)


prompt = ':set temp 2.0  '

cmd = Command()

action, *args = prompt[1:].strip().split()


def execute(action: str, *args: str) -> None:
    try:
        getattr(cmd, action)(*args)
    except (AttributeError, TypeError) as e:
        if isinstance(e, AttributeError):
            print(f'Unknown command: {action}')
        elif isinstance(e, TypeError):
            print(f'Invalid arguments: {args}')
        else:
            print('Unknown error')


tests = [
    ':set temp 2.0',
    ':set color red',
    # trigger erros,
    ':set temp',
    ':set color',
    ':set txxx 2.0',
    ':set color red blue',
    ':xxx temp 2.0',
]

for test in tests:
    action, *args = test[1:].strip().split()
    execute(action, *args)
    print(settings.__dict__)
