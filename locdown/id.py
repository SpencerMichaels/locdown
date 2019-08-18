from collections import namedtuple
from enum import Enum
import functools
import os
import random
import re
import time

from . import jukebox, parser, util

ID = namedtuple('ID', 'value type_')
IDRange = namedtuple('IDRange', 'start end type_')
IDRandom = namedtuple('IDRandom', 'count type_')

ID_RANGE_REGEX = re.compile('^(\d+)-(\d+)$')
ID_RANDOM_REGEX = re.compile('^random(\d+)?$')

ID_ARTIST_PREFIX = 'artist:'

class IDType(Enum):
  RECORDING = 'recording'
  ARTIST = 'artist'

MAX_ID_UPDATE_INTERVAL = 24 * 60 * 60 # One day, in seconds
MAX_ID_VALUES = {
    IDType.RECORDING: 10330, # Accurate as of August 13, 2019
    IDType.ARTIST:    1,     # TODO
}

def parse_id(arg):
  type_ = IDType.RECORDING
  if arg.startswith(ID_ARTIST_PREFIX):
    arg = arg[len(ID_ARTIST_PREFIX):]
    type_ = IDType.ARTIST

  if arg.isnumeric():
    return ID(int(arg), type_)

  match = ID_RANGE_REGEX.match(arg)
  if match:
    start, end = map(int, match.groups())
    return IDRange(start, end, type_)

  match = ID_RANDOM_REGEX.match(arg)
  if match:
    count = int(match.group(1)) if match.group(1) else 1
    return IDRandom(count, type_)

  id_, type_ = jukebox.url.url_to_id(arg)
  return ID(id_, type_)

def get_max_id_filepath(type_):
  return os.path.join(util.USER_DATA_DIR, f'max_{type_.value}_id')

def max_id_needs_update(type_):
  filepath = get_max_id_filepath(type_)
  if not os.path.isfile(filepath):
    return True
  mtime = os.path.getmtime(filepath)
  elapsed = time.time() - mtime
  return elapsed > MAX_ID_UPDATE_INTERVAL

def get_max_id(type_):
  filepath = get_max_id_filepath(type_)
  saved_value = None
  if os.path.exists(filepath):
    with open(filepath, 'r') as f:
      saved_value = int(f.read())
  return saved_value

async def update_max_id(type_, session):
  saved_value = get_max_id(type_)
  new_value = await jukebox.find_max_valid_id(
      session, type_.value + 's',
      saved_value or MAX_ID_VALUES[type_])

  filepath = get_max_id_filepath(type_)
  if new_value != saved_value:
    with open(filepath, 'w') as f:
      f.write(str(new_value))
  return new_value

async def expand_ids(session, ids):
  types = { id_.type_ for id_ in ids }
  types_needing_upper_bound = { id_.type_ for id_ in ids if type(id_) in [IDRandom] }

  for type_ in types:
    if type_ in types_needing_upper_bound and max_id_needs_update(type_):
      util.log('Enumerating the LoC catalog, please wait...')
      MAX_ID_VALUES[type_] = await update_max_id(type_)
    else:
      MAX_ID_VALUES[type_] = get_max_id(type_)

  expand_ids_to_type = lambda type_, ids: map(lambda id_: ID(id_, type_), ids)
  converters = {
    ID:        lambda arg: [arg],
    IDRange:   lambda arg: expand_ids_to_type( \
        arg.type_, range(arg.start, arg.end+1)),
    IDRandom:  lambda arg: expand_ids_to_type( \
        arg.type_, random.sample(range(1, 1 + max_id), arg.count)),
  }

  return functools.reduce(lambda expanded_ids, arg: \
      expanded_ids + list(converters[type(arg)](arg)), ids, [])
