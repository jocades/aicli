from rich.markdown import Markdown
from rich import print


res = '''
This is just some normal text.

A list:
- item 1
- item 2

```python
print("Hello, World!")
```
```javascript
console.log("Hello, World!")
```
'''

for w in res.splitlines():
    print(Markdown(w), end='', flush=True)
