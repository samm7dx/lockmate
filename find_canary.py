import json, os, unicodedata, base64, binascii, re
from pathlib import Path

def with_b64(text):
    _B64 = re.compile(r'[A-Za-z0-9+/]{24,}={0,2}')
    extra = []
    for m in _B64.finditer(text):
        tok = m.group(0)
        try:
            extra.append(base64.b64decode(tok + '=' * (-len(tok) % 4)).decode('utf-8', errors='ignore'))
        except (binascii.Error, ValueError):
            pass
    return text + '\n' + '\n'.join(extra) if extra else text

def read_text(p):
    try:
        raw = p.read_bytes()[: 50 * 1024 * 1024]
    except OSError:
        return ''
    return with_b64(raw.decode('utf-8', errors='replace'))

def all_text_under(root):
    parts = []
    for dp, _, fn in os.walk(root):
        for n in fn:
            parts.append(n)
            parts.append(read_text(Path(dp) / n))
    return ' '.join(unicodedata.normalize('NFKC', '\n'.join(parts)).casefold().split())

out = Path('.artifacts/toolkit/phase4-output-final')
everything = all_text_under(out)

canary = 'Tsering Wangmo'
canary_norm = ' '.join(unicodedata.normalize('NFKC', canary).casefold().split())
if canary_norm in everything:
    print('FOUND:', canary)
    # Find which file
    for dp, _, fn in os.walk('.artifacts/toolkit/phase4-output-final'):
        for n in fn:
            p = Path(dp) / n
            try:
                content = read_text(p)
                if canary.lower() in content.lower():
                    rel = p.relative_to(Path('.artifacts/toolkit/phase4-output-final'))
                    print(f'  IN FILE: {rel}')
            except:
                pass
else:
    print('NOT FOUND:', canary)