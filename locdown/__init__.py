import asyncio
import aiohttp
from fake_useragent import UserAgent

import contextlib
import json
import os
import shutil
import signal

from . import disclaimer, id, parser, tagger, util
from . import jukebox as jb

# Global state for tracking temporary files, metadata, etc. across tasks
STATE = type('', (), {})()
SCRAPERS = {
    id.IDType.ARTIST: jb.scraper.scrape_artist_details,
    id.IDType.RECORDING: jb.scraper.scrape_recording_details,
}

def stringify_metadata(metadata):
  return json.dumps(metadata, indent=2, sort_keys=True, ensure_ascii=False)

def expand_dest_dir(dest):
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
    exit(0)

  expanded_ids = await id.expand_ids(session, args.recordings)
  dest_dir = expand_dest_dir(args.dest)

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
      metadata = await SCRAPERS[id_.type_](session, id_.id_)

    tmp_filepath = os.path.join(dest_dir, f'{id_}.mp3.tmp')

    STATE.tmpfiles.add(tmp_filepath)
    try:
      await jb.download_recording(id_, args.bitrate, tmp_filepath)
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
    tasks.add(asyncio.create_task(download_task(STATE, ids.pop(0))))
  await asyncio.wait(tasks)
  util.log('')

  if args.print and metadata:
    print(stringify_metadata(STATE.metadata))

async def scrape(session, args):
  if args.artist_dirs and not args.save_json:
    util.die('-r/--artist-dirs must be used with -j/--save-json')

  expanded_ids = await id.expand_ids(session, args.recordings)

  normalized_ids = {}
  for id_type in list(id.IDType):
    normalized_ids[id_type] = [ id_.value for id_ in expanded_ids if id_.type_ == id_type ]

  def get_metadata(scrape_fn, id_type, *args):
    return asyncio.gather(*map(
      lambda id_: scrape_fn(id_),
      normalized_ids.get(id_type)))

  artist_metadata = await get_metadata(
      lambda id_: \
          jb.scraper.scrape_artist_details(session, id_, args.shallow),
      id.IDType.ARTIST)
  recording_metadata = await get_metadata(
      lambda id_: \
        jb.scraper.scrape_recording_details(session, id_),
      id.IDType.RECORDING)

  if args.save_json:
    dest_dir = expand_dest_dir(args.dest)

    def write_metadata(filepath, md):
      with open(filepath + '.json', 'w', encoding='utf-8') as f:
        f.write(stringify_metadata(md))
        f.write('\n')

    for md in artist_metadata:
      name = f'{md.get(jb.keys.ID)} - {md.get(jb.keys.REF_NAME)}'
      if args.artist_dirs:
        path = os.path.join(dest_dir, name)
        if os.path.isdir(path):
          util.log(f'The target path already exists:\n  {path}\nRemove it? (y/N)')
          if util.confirm(default='N'):
            os.rmdir(path) # TODO: handle nonempty dirs
            os.mkdir(path)
        else:
          os.mkdir(path)
        for rmd in md.get(jb.keys.RECORDINGS):
          filename = f'{rmd.get(jb.keys.ID)} - {md.get(jb.keys.REF_NAME)} - {rmd.get(jb.keys.TITLE)}' \
            if args.shallow \
            else tagger.make_filename(rmd)
          write_metadata(os.path.join(path, filename), rmd)
        del md[jb.keys.RECORDINGS]
        write_metadata(os.path.join(path, 'artist'), md)
      else:
        write_metadata(name, md)

    for md in recording_metadata:
      filepath = os.path.join(dest_dir, tagger.make_filename(md))
      write_metadata(filepath, md)

  elif artist_metadata and recording_metadata:
    artist_metadata.append({
        jb.keys.REF_NAME: 'Various Artists',
        jb.keys.RECORDINGS: recording_metadata
    })
    print(stringify_metadata(artist_metadata))
  else:
    print(stringify_metadata(recording_metadata or artist_metadata))


async def stream(session, args):
  expanded_ids = await id.expand_ids(session, args.recordings)

  async def normalize_id(id_):
    if id_.type_ == id.IDType.ARTIST:
      metadata = await jb.scraper.scrape_artist_details(session, id_.value, shallow=True)
      return [ entry.get(jb.keys.ID) for entry in metadata.get(jb.keys.RECORDINGS) ]
    else:
      return [id_.value]

  normalized_ids = util.flatten(await asyncio.gather(*map(normalize_id, expanded_ids)))
  urls = map(lambda id_: jb.url.id_to_stream_url(id_, args.bitrate), normalized_ids)

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
    raise e
    util.die(str(e))
