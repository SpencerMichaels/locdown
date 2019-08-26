import argparse, re

from . import disclaimer, id, jukebox

class DisclaimerAction(argparse.Action):
  def __call__(self, parser, namespace, values, option_string=None):
    disclaimer.show()
    parser.exit()

ID_RANGE_REGEX = re.compile('^(\d+)-(\d+)$')
ID_RANDOM_REGEX = re.compile('^random(\d+)?$')
ID_ARTIST_PREFIX = 'artist:'

def parse_recordings_argument(arg):
  type_ = id.IDType.RECORDING
  if arg.startswith(ID_ARTIST_PREFIX):
    arg = arg[len(ID_ARTIST_PREFIX):]
    type_ = id.IDType.ARTIST

  if arg.isnumeric():
    return id.ID(int(arg), type_)

  match = ID_RANGE_REGEX.match(arg)
  if match:
    start, end = map(int, match.groups())
    return id.IDRange(start, end, type_)

  match = ID_RANDOM_REGEX.match(arg)
  if match:
    count = int(match.group(1)) if match.group(1) else 1
    return id.IDRandom(count, type_)

  id_, type_ = jukebox.url.url_to_id(arg)
  return ID(id_, type_)

def add_recordings_argument(parser, verb):
  parser.add_argument('recordings', metavar='recording', nargs='+', default=[],
      type=parse_recordings_argument,
      help=f'The recording(s) to {verb}; see below for details.')

EPILOG=\
'''Recordings can be specified in a combination of the following formats:
- A details page URL: `https://loc.gov/jukebox/recordings/detail/id/1234`
- A plain ID: `1234`
- A range of IDs (inclusive): `123-234`
- One or more randomly-selected IDs: `randomN` for `N` IDs, e.g. `random10`. 
  `random1` can be abbreviated as `random`.\n
Artist IDs can also be specified
- An details page URL: `https://loc.gov/jukebox/artists/detail/id/1234`
- A plain ID, range of IDs, or random selection of IDs prefixed with `artist:`
  - `artist:1234`
  - `artist:123-123`
  - `artist:random10`\n
In stream and download mode, an artist ID is equivalent to a list
of all the IDs of the recordings credited to that artist. In scrape
mode, some data about the artist\' will be downloaded in addition
to the full list of recordings. See README.md for details.
'''

def make_arg_parser():
    root = argparse.ArgumentParser(prog='locdown', description=
        'Fetch audio and metadata from the Library of Congress Jukebox\n' + \
        '(https://www.loc.gov/jukebox).')
    root.add_argument('-m', '--max-connections', type=int, default=10, help=
        'The maximum number of simultaneous connections to make. Defaults to 10.')

    subparsers = root.add_subparsers(dest='action', metavar='action', required=True)

    stream = subparsers.add_parser('stream', epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help= 'Stream audio in your OS\'s local media player.')
    stream.add_argument('-b', '--bitrate', type=int, default=320, help=
        'Desired bitrate, in kbps. Can be 128 or 320. Defaults to 320.')
    stream.add_argument('-p', '--print', action='store_true', help=
        'Print stream URLs instead of opening them.')
    add_recordings_argument(stream, 'stream')

    scrape = subparsers.add_parser('scrape', epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='Scrape audio metadata.')
    scrape.add_argument('-s', '--shallow', action='store_true', help=
        'When scraping an artist\'s details page, only use the recording information ' + \
        'available on that page; don\'t fetch the full details for those recordings.')
    scrape.add_argument('-r', '--artist-dirs', action='store_true', help=
        'Save artist information as a directory containing individual JSON files ' + \
        'for each recording, rather than the default of a single JSON file.')
    scrape.add_argument('-j', '--save-json', action='store_true', help=
        'Save individual JSON data files for each recording instead of printing.')
    scrape.add_argument('-d', '--dest', type=str, default='.', help=
        'Destination directory for downloaded data files. Use with the -s flag.')
    add_recordings_argument(scrape, 'scrape')

    download = subparsers.add_parser('download', epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='Download audio.')
    download.add_argument('-d', '--dest', type=str, default='.', help=
        'Destination directory for downloaded recordings and data files.')
    download.add_argument('-b', '--bitrate', type=int, default=320, help=
        'Desired bitrate (128 or 320). Defaults to 320.')
    download.add_argument('-t', '--tag', action='store_true', help=
        'Tag the downloaded recording(s).')
    download.add_argument('-a', '--art', action='store_true', help=
        'Download album art, if available, and embed it in the recording(s).')
    download.add_argument('-p', '--print', action='store_true', help=
        'Print JSON data for the recording(s); same as the `scrape` action.')
    download.add_argument('-j', '--save-json', action='store_true', help=
        'Save individual JSON data files alongside each recording.')
    download.add_argument('-r', '--artist-dirs', action='store_true', help=
        'For each artist ID specified, save all of the artists\' recordings ' + \
        'in artist-specific directories.')
    add_recordings_argument(download, 'download')
    download.register('action', 'disclaimer', DisclaimerAction)
    download.add_argument('--disclaimer', nargs=0, action='disclaimer', help=
        'Show the disclaimer displayed when download mode is first used.')

    return root

def parse_args(argv):
  return make_arg_parser().parse_args(argv)
