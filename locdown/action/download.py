from pathlib import Path
import os, shutil

from .common import expand_dest_dir, stringify_metadata
from ..taskbatch import TaskBatch
from ..progressbar import ProgressBar
from ..progressbar.widget import Bar, Fraction, Percent, Spinner
from .. import disclaimer, id, tagger, util
from .. import jukebox as jb
from .scrape import scrape_inner

def validate_args(args):
  if not shutil.which('rtmpdump'):
    util.die('Dependency rtmpdump not found. Please install it.')
  elif not args.bitrate in [128, 320]:
    util.die('Bitrate must be either 128 or 320.')
  elif args.dest and not os.path.exists(args.dest):
    util.die(f'The destination specified by -d/--dest does not exist:\n  {args.dest}')
  elif args.dest and not os.path.isdir(args.dest):
    util.die(f'The destination specified by -d/--dest exists, but is not a directory:\n  {args.dest}')

async def download(session, args, max_connections=10):
  validate_args(args)

  if args.disclaimer:
    disclaimer.show()
    exit(0)
  elif not disclaimer.accepted() and not disclaimer.ask():
    util.die('You must accept the terms of the disclaimer before using download mode.')

  # Songs for each artist are obtained in shallow format first; full metadata
  # is fetched just before each recording is downloaded. This is slightly less
  # efficient than fetching the full data initially, (though it still doesn't take
  # any extra page requests), but makes the progress indicators more sensible for
  # the user. Previously, the progress bar would sit still while locdown
  # fetched all the metadata for an artist's songs at once, which gives the
  # impression of hanging.
  recording_metadata, artist_metadata = await scrape_inner(
      session, args.recordings,
      dest=args.dest or '' if args.save_json else None,
      artist_dirs=args.artist_dirs, shallow=True)

  async def download_task(metadata, dest_dir):
    id_ = metadata.get(jb.keys.ID)
    tmp_filepath = dest_dir.joinpath(f'{id_}.mp3.tmp')

    try:
      await jb.download_recording(id_, args.bitrate, str(tmp_filepath))
    except RuntimeError as e:
      util.eprint(f'warning: Failed to download recording #{id_}: {str(e)}')
      if tmp_filepath.is_file():
        tmp_filepath.unlink()
      return

    if args.tag:
      await tagger.tag(tmp_filepath, metadata, session if args.art else None)
      final_filepath = dest_dir.joinpath(tagger.make_filename(metadata))
    else:
      final_filepath = tmp_filepath.with_suffix('.mp3')

    tmp_filepath.rename(Path(str(final_filepath) + '.mp3'))

  async def download_task_unshallow(metadata, dest_dir):
    return await download_task(await jb.scrape_recording(session, metadata.get(jb.keys.ID)), dest_dir)

  dest_dir = expand_dest_dir(args.dest)
  tasks = [ download_task(md, dest_dir) \
            for md in recording_metadata ]
  for artist in artist_metadata:
    artist_dest_dir = dest_dir.joinpath(
        f'{artist.get(jb.keys.ID)} - {artist.get(jb.keys.REF_NAME)}')
    tasks += [ download_task_unshallow(md, artist_dest_dir) \
               for md in artist.get(jb.keys.RECORDINGS) or [] ]

  bar = ProgressBar(left_fmt='%s %s (%s) %s',
                    left=[Spinner(), Fraction(), Percent(), Bar()])
  monitor = lambda state: util.eprint(f'\r{bar(state)}',
      end='\n' if state.num_total == state.num_done else '')

  util.eprint('Downloading recordings...')
  batch = TaskBatch(tasks, limit=max_connections,
                    monitor=monitor, monitor_interval=bar.update_interval)
  await batch.run()
