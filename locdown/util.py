from appdirs import user_data_dir
import functools, operator, os, sys, subprocess

USER_DATA_DIR = user_data_dir("locdown", "SpencerMichaels", roaming=False)

def die(msg, errno=1):
  log(f'error: {msg}')
  exit(errno)

def log(msg, end='\n'):
  print(msg, file=sys.stderr, end=end)

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
    log('Invalid input. Please enter Y/yes or N/no.', file=sys.stderr)
    result = read_yn(input())

  return result

def flatten(l):
  return functools.reduce(operator.add, l, [])

def open_urls(files):
  if sys.platform == 'win32':
    for f in files:
      os.startfile(f'"{f}"')
  else:
    opener = 'open' if sys.platform == 'darwin' else 'xdg-open'
    subprocess.call([opener] + files)

#def unlist1(l):
#  return l[0] if len(l) == 1 else l
