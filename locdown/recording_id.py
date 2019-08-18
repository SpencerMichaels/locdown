import functools
import os
import random
import time

from . import jukebox, parser, util

MAX_RECORDING_ID_INITIAL_VALUE = 10330 # Accurate as of August 13, 2019
MAX_RECORDING_ID_FILE = os.path.join(util.USER_DATA_DIR, 'max_recording_id')
MAX_RECORDING_ID_UPDATE_INTERVAL = 24 * 60 * 60 # one day, in seconds

async def recordings_args_to_concrete_ids(session, recordings):
  arg_needs_range_bounds = lambda arg: type(arg) in [parser.IDRandom]

  # If the args list contains a "random" element, we have to figure out the
  # range of IDs we can select from: we need to know the maximum valid
  # recording ID. TODO: Should "range" elements also be checked here, or should
  # we rely on 404s when retrieval is attempted? Probably the latter.

  if max_recording_id_needs_update() and any(map(arg_needs_range_bounds, recordings)):
    util.log('Enumerating the LoC catalog, please wait...')
    max_id = await update_max_recording_id(session)
  else:
    max_id = get_max_recording_id()

  converters = {
    parser.ID:        lambda arg: [arg],
    parser.IDRange:   lambda arg: list(range(arg.start, arg.end+1)), # TODO
    parser.IDRandom:  lambda arg: random.sample(range(1, 1 + max_id), arg.count)
  }

  return functools.reduce(lambda ids, arg: \
      ids + converters[type(arg)](arg), recordings, [])

def max_recording_id_needs_update():
  if not os.path.isfile(MAX_RECORDING_ID_FILE):
    return True
  mtime = os.path.getmtime(MAX_RECORDING_ID_FILE)
  elapsed = time.time() - mtime
  return elapsed > MAX_RECORDING_ID_UPDATE_INTERVAL

def get_max_recording_id():
  saved_value = None
  if os.path.exists(MAX_RECORDING_ID_FILE):
    with open(MAX_RECORDING_ID_FILE, 'r') as f:
      saved_value = int(f.read())
  return saved_value

async def update_max_recording_id(session):
  saved_value = get_max_recording_id()
  new_value = await jukebox.find_max_valid_recording_id(
      session, saved_value or MAX_RECORDING_ID_INITIAL_VALUE)
  if new_value != saved_value:
    with open(MAX_RECORDING_ID_FILE, 'w') as f:
      f.write(str(new_value))
  return new_value
