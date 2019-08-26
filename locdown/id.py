from collections import namedtuple
from enum import Enum
import functools, pathlib, random, re, time

from . import config, util
from . import jukebox

ID = namedtuple('ID', 'value type_')
IDRange = namedtuple('IDRange', 'start end type_')
IDRandom = namedtuple('IDRandom', 'count type_')

class IDType(Enum):
  RECORDING = 'recording'
  ARTIST = 'artist'

MAX_ID_UPDATE_INTERVAL = 24 * 60 * 60 # One day, in seconds
MAX_ID_VALUES = { # Accurate as of August 26, 2019
    IDType.RECORDING: 10330,
    IDType.ARTIST: 6542
}

def get_max_id_path(type_):
  return config.USER_DATA_DIR.joinpath(f'max_{type_.value}_id')

def max_id_needs_update(type_):
  path = get_max_id_path(type_)
  if not path.is_file():
    return True
  mtime = path.stat().st_mtime
  elapsed = time.time() - mtime
  return elapsed > MAX_ID_UPDATE_INTERVAL

def get_max_id(type_):
  path = get_max_id_path(type_)
  if path.is_file():
    with path.open('r') as f:
      return int(f.read())
  return None

async def update_max_id(type_, session):
  util.eprint(f'Enumerating {type_.value}s...')

  saved_value = get_max_id(type_)
  new_value = await jukebox.find_max_valid_id(
      session, type_.value + 's',
      saved_value or MAX_ID_VALUES[type_])

  path = get_max_id_path(type_)
  if new_value != saved_value:
    with path.open('w') as f:
      f.write(str(new_value))
  else:
    path.touch()
  return new_value

async def expand_ids(session, ids):
  types = { id_.type_ for id_ in ids }
  types_needing_upper_bound = { id_.type_ for id_ in ids if type(id_) in [IDRandom] }

  for type_ in types:
    MAX_ID_VALUES[type_] = await update_max_id(type_, session) \
        if type_ in types_needing_upper_bound and max_id_needs_update(type_) \
        else get_max_id(type_)

  expand_ids_to_type = lambda type_, ids: map(lambda id_: ID(id_, type_), ids)
  converters = {
    ID:        lambda arg: [arg],
    IDRange:   lambda arg: expand_ids_to_type( \
        arg.type_, range(arg.start, arg.end+1)),
    IDRandom:  lambda arg: expand_ids_to_type( \
        arg.type_, random.sample(range(1, 1 + MAX_ID_VALUES[type_]), arg.count)),
  }

  return functools.reduce(lambda expanded_ids, arg: \
      expanded_ids + list(converters[type(arg)](arg)), ids, [])
