from rich.markdown import Markdown
from rich import print


md = '''
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

print(Markdown(md))
