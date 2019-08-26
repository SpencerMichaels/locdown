from importlib.resources import read_text

from .. import config, util

_ACCEPTED_PATH = config.USER_DATA_DIR.joinpath('accepted_disclaimer')

def accepted():
  return _ACCEPTED_PATH.is_file()

def ask():
  show()
  util.eprint(f'Do you agree to the above terms? (Y/N)')

  result = util.confirm()
  if result:
    _ACCEPTED_PATH.touch()
  elif _ACCEPTED_PATH.is_file():
    _ACCEPTED_PATH.unlink()

  return result

def show():
  text = read_text('locdown.disclaimer', 'DISCLAIMER.txt')
  util.eprint(f'\n{text}')
