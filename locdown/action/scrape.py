from pathlib import Path

from .common import expand_dest_dir, stringify_metadata
from ..taskbatch import TaskBatch
from ..progressbar import ProgressBar
from ..progressbar.widget import Bar, Fraction, Percent, Spinner
from .. import id, tagger, util
from .. import jukebox as jb

MISC_RECORDINGS_ARTIST = 'Various Artists'

def validate_args(args):
  if args.artist_dirs and not args.save_json:
    util.die('-r/--artist-dirs must be used with -j/--save-json')

def write_metadata(filepath, md):
  with Path(str(filepath) + '.json').open('w', encoding='utf-8') as f:
    f.write(stringify_metadata(md))
    f.write('\n')

def save_artist_metadata(dest_dir, md, artist_dirs=False, shallow=False):
  name = f'{md.get(jb.keys.ID)} - {md.get(jb.keys.REF_NAME)}'
  path = dest_dir.joinpath(name)
  if artist_dirs:
    path.mkdir(exist_ok=True)
    for rmd in md.get(jb.keys.RECORDINGS):
      filename = f'{rmd.get(jb.keys.ID)} - {md.get(jb.keys.REF_NAME)} - {rmd.get(jb.keys.TITLE)}' \
        if shallow \
        else tagger.make_filename(rmd)
      write_metadata(path.joinpath(filename), rmd)
    mdw = dict(md)
    del mdw[jb.keys.RECORDINGS]
    write_metadata(path.joinpath('artist'), mdw)
  else:
    write_metadata(path, md)

def save_recording_metadata(dest_dir, md):
  filepath = dest_dir.joinpath(tagger.make_filename(md))
  write_metadata(filepath, md)

async def scrape_inner(session, recordings, dest=None, artist_dirs=False, shallow=False):
  dest_dir = expand_dest_dir(dest) if dest else None
  expanded_ids = await id.expand_ids(session, recordings)

  normalized_ids = {}
  for id_type in list(id.IDType):
    ids_of_type = [ id_.value for id_ in expanded_ids if id_.type_ == id_type ]
    if ids_of_type:
      normalized_ids[id_type] = ids_of_type

  bar = ProgressBar(left_fmt='%s %s (%s) %s',
                    left=[Spinner(), Fraction(), Percent(), Bar()])
  monitor = lambda state: util.eprint(f'\r{bar(state)}',
      end='\n' if state.num_total == state.num_done else '')

  def scrape_metadata_task(scrape_fn, id_type):
    tasks = map(scrape_fn, normalized_ids.get(id_type))
    batch = TaskBatch(tasks, monitor=monitor, monitor_interval=bar.update_interval)
    return batch.run()

  artist_metadata = {}
  if id.IDType.ARTIST in normalized_ids:
    async def scrape_fn(id_):
      try:
        result = await jb.scrape_artist(session, id_, shallow)
        if dest_dir:
          save_artist_metadata(dest_dir, result, artist_dirs=artist_dirs, shallow=shallow)
        return result
      except RuntimeError as e:
        util.eprint(f'warning: Failed to scrape metadata for artist #{id_}: {str(e)}')

    util.eprint('Scraping artist metadata...')
    artist_metadata = await scrape_metadata_task(scrape_fn, id.IDType.ARTIST)

  recording_metadata = {}
  if id.IDType.RECORDING in normalized_ids:
    async def scrape_fn(id_):
      try:
        result = await jb.scrape_recording(session, id_)
        if dest_dir:
          save_recording_metadata(dest_dir, result)
        return result
      except Exception as e:
        util.eprint(f'warning: Failed to scrape metadata for recording #{id_}: {str(e)}')

    util.eprint('Scraping recording metadata...')
    recording_metadata = await scrape_metadata_task(scrape_fn, id.IDType.RECORDING)

  return (recording_metadata, artist_metadata)

def finalize_metadata(artist_metadata, recording_metadata, artist_dirs=False):
  if artist_dirs or (artist_metadata and recording_metadata):
    artist_metadata.append({
        jb.keys.REF_NAME: MISC_RECORDINGS_ARTIST,
        jb.keys.RECORDINGS: recording_metadata
    })
  return [ md for md in artist_metadata or recording_metadata if md != None ]

async def scrape(session, args):
  validate_args(args)

  dest = args.dest or '' if args.save_json else None
  recording_metadata, artist_metadata = await scrape_inner(
      session, args.recordings,
      dest=dest, artist_dirs=args.artist_dirs, shallow=args.shallow)

  if not args.save_json:
    print(stringify_metadata(finalize_metadata(artist_metadata, recording_metadata)))
