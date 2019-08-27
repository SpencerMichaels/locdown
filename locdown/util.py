import functools, operator, os, sys, subprocess

def eprint(*args, **kwargs):
  print(*args, file=sys.stderr, **kwargs)

def die(msg, errno=1):
  eprint(f'error: {msg}')
  exit(errno)

def a_an(s):
  if not s:
    return s
  prefix = 'an' if s[0] in 'aeiou' else 'a'
  return f'{prefix} {s}'

def pluralize(s, n):
  if n > 1:
    return s + 's'
  return s

def confirm(default=None):
  def read_yn(s):
    if not s.strip() and default != None:
      return default
    elif s.lower() in ['y', 'yes']:
      return True
    elif s.lower() in ['n', 'no']:
      return False
    else:
      return None

  result = read_yn(input())
  while result == None:
    eprint('Invalid input. Please enter y/yes or n/no (case-insensitive).', file=sys.stderr)
    result = read_yn(input())

  return result

def flatten(l):
  return functools.reduce(operator.add, l, [])

def open_urls(urls):
  if sys.platform == 'win32':
    for f in urls:
      os.startfile(f'"{f}"')
  else:
    opener = 'open' if sys.platform == 'darwin' else 'xdg-open'
    subprocess.call([opener] + urls)
