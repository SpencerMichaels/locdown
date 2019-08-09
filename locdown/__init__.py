import asyncio
import aiohttp
from fake_useragent import UserAgent

import contextlib
import json
import os
import shutil
import signal

from . import disclaimer, jukebox, parser, tagger, util
from . import recording_id as rid

# Global state for tracking temporary files, metadata, etc. across tasks
STATE = type('', (), {})()

def stringify_metadata(metadata):
  return json.dumps(metadata, indent=2, sort_keys=True)

def get_dest_dir(dest):
  return os.path.expanduser(dest) if dest else ''

async def download(session, args, max_connections=10):
  if not shutil.which('rtmpdump'):
    util.die('Dependency rtmpdump not found. Please install it.')
  elif not args.bitrate in [128, 320]:
    util.die('Bitrate must be either 128 or 320.')
  elif args.dest and not os.path.exists(args.dest):
    util.die(f'The destination specified by -d/--dest does not exist:\n  {args.dest}')
  elif args.dest and not os.path.isdir(args.dest):
    util.die(f'The destination specified by -d/--dest exists, but is not a directory:\n  {args.dest}')
  elif not disclaimer.accepted() and not disclaimer.ask():
    util.die('You must accept the terms of the disclaimer before using download mode.')
  elif args.disclaimer:
    disclaimer.show()
    return

  ids = await rid.recordings_args_to_concrete_ids(session, args.recordings)
  dest_dir = get_dest_dir(args.dest)

  STATE.total_downloaded = 0
  STATE.to_download = len(ids)
  STATE.tmpfiles = set()
  STATE.metadata = []

  util.log(f'Downloading {STATE.to_download} {util.pluralize("recording", STATE.to_download)}...')

  def print_status(STATE):
    percent = (100*STATE.total_downloaded)//STATE.to_download
    util.log(f'\r{STATE.total_downloaded}/{STATE.to_download} ({percent}%) complete', end='')

  async def download_task(STATE, id_):
    metadata = None
    if args.tag or args.save_json:
      metadata = await jukebox.scrape(session, id_)

    tmp_filepath = os.path.join(dest_dir, f'{id_}.mp3.tmp')

    STATE.tmpfiles.add(tmp_filepath)
    try:
      await jukebox.download_recording(id_, args.bitrate, tmp_filepath)
    except RuntimeError:
      STATE.total_downloaded += 1
      print_status(STATE)
      util.log(f'    warning: Failed to download recording #{id_}. The audio may be unavailable.')
      os.remove(tmp_filepath)
      STATE.tmpfiles.remove(tmp_filepath)
      return

    if args.tag:
      await tagger.tag(tmp_filepath, metadata, session if args.art else None)
      final_filepath = os.path.join(dest_dir, tagger.make_filename(metadata))
      filepath = final_filepath + '.mp3'
    else:
      filepath = tmp_filepath[:-4]

    os.rename(tmp_filepath, filepath)
    STATE.tmpfiles.remove(tmp_filepath)

    if args.save_json:
      with open(filepath[:-4] + '.json', 'w') as f:
        f.write(stringify_metadata(metadata))
        f.write('\n')

    STATE.metadata.append(metadata)
    STATE.total_downloaded += 1
    print_status(STATE)

  print_status(STATE)

  tasks = set()
  while ids:
    if len(tasks) >= max_connections:
      _, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    tasks.add(asyncio.create_task(download_task(STATE, ids.pop(00))))
  await asyncio.wait(tasks)
  util.log('')

  if args.print and metadata:
    print(stringify_metadata(STATE.metadata))

async def scrape(session, args):
  ids = await rid.recordings_args_to_concrete_ids(session, args.recordings)
  tasks = map(lambda id_: jukebox.scrape(session, id_), ids)
  metadata = await asyncio.gather(*tasks)

  if args.save_json:
    dest_dir = get_dest_dir(args.dest)
    for md in metadata:
      filepath = os.path.join(dest_dir, tagger.make_filename(md))
      with open(filepath + '.json', 'w') as f:
        f.write(stringify_metadata(md))
        f.write('\n')
  else:
    print(stringify_metadata(metadata))

async def stream(session, args):
  ids = await rid.recordings_args_to_concrete_ids(session, args.recordings)
  urls = map(lambda id_: jukebox.url.id_to_stream_url(id_, args.bitrate), ids)
  if (args.print):
    for url in urls:
      print(url)
  else:
    util.open_urls(list(urls))

async def main_task(args):
  async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(limit=args.max_connections),
        headers={ 'User-Agent': UserAgent().chrome }) as session:
    if args.action == 'download':
      await download(session, args, args.max_connections)
    elif args.action == 'scrape':
      await scrape(session, args)
    elif args.action == 'stream':
      await stream(session, args)

def cleanup_tmpfiles():
  if STATE.tmpfiles:
    print('\n\nInterrupted mid-download. ' + \
         f'There are currently {len(STATE.tmpfiles)} temporary files; remove them? (Y/n)')
    if util.confirm(default=True):
      for tmpfile in sorted(STATE.tmpfiles):
        if os.path.isfile(tmpfile):
          os.remove(tmpfile)
          util.log(f'Removed \'{tmpfile}\'')

def main(argv):
  if not os.path.isdir(util.USER_DATA_DIR):
    os.makedirs(util.USER_DATA_DIR)

  args = parser.make_parser().parse_args(argv)

  try:
    loop = asyncio.get_event_loop()
    worker = asyncio.ensure_future(main_task(args))
    loop.run_until_complete(worker)
    exit(0)

  except KeyboardInterrupt:
    worker.cancel()
    with contextlib.suppress(asyncio.CancelledError):
      loop.run_until_complete(worker)
    cleanup_tmpfiles()
    exit(0)

  except Exception as e:
    util.die(str(e))
