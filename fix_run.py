import re

path = r'C:\Users\Lalithaya\Downloads\skylark-bi-agent\agent.py'

with open(path, encoding='utf-8') as f:
    content = f.read()

# Replace the run() function to return a dict instead of a string
old = 'def run(question: str) -> str:\n    return run_agent(_get_agent(), question)'
new = 'def run(question: str):\n    answer = run_agent(_get_agent(), question)\n    return {"intent": "agent", "answer": answer, "content": answer}'

if old in content:
    content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('FIXED — run() now returns dict')
else:
    # Try without type hint
    old2 = 'def run(question):\n    return run_agent(_get_agent(), question)'
    if old2 in content:
        content = content.replace(old2, new)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print('FIXED — run() now returns dict')
    else:
        print('Pattern not found. Current run() definition:')
        for i, line in enumerate(content.split('\n')):
            if 'def run(' in line:
                start = max(0, i-1)
                print('\n'.join(content.split('\n')[start:start+6]))
