from importlib.resources import read_text
import os.path

from . import resources, util

ACCEPTED_FILE = os.path.join(util.USER_DATA_DIR, 'accepted_disclaimer')

def accepted():
  return os.path.isfile(ACCEPTED_FILE)

def ask():
  show()
  util.log(f'Do you agree to the above terms? (Y/N)')

  result = util.confirm()
  if result:
    open(ACCEPTED_FILE, 'a').close() # Create the file
  elif os.path.isfile(ACCEPTED_FILE):
    os.remove(ACCEPTED_FILE)

  return result

def show():
  text = read_text(resources, 'DISCLAIMER.txt')
  util.log(f'\n{text}')
