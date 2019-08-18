import argparse

from . import disclaimer, id, jukebox, util

class DisclaimerAction(argparse.Action):
  def __call__(self, parser, namespace, values, option_string=None):
    disclaimer.show()
    parser.exit()

def add_recordings_argument(parser, verb):
  help_text=f'''The recording(s) to {verb}.

Recordings can be specified in four ways:
(1) A URL of the details page for a recording, e.g.
    https://loc.gov/jukebox/recordings/detail/id/1234
(2) Just the ID found in the URL: `1234`
(3) A dash-separated range of IDs: 100-120
(4) N random IDs: `random{{N}}`, e.g. `random10`.
    `random1` can be abbreviated as `random`.
'''

  parser.add_argument('recordings', metavar='recording', nargs='+', default=[],
      type=id.parse_id, help=help_text)

def make_parser():
    root = argparse.ArgumentParser(prog='locdown', description=
        'Fetch audio and metadata from the Library of Congress Jukebox ' + \
        '(https://www.loc.gov/jukebox).')

    root.add_argument('-m', '--max-connections', type=int, default=10, help=
        'The maximum number of simultaneous connections to make. Defaults to 10.')

    subparsers = root.add_subparsers(dest='action', metavar='action', required=True)

    stream = subparsers.add_parser('stream', formatter_class=argparse.RawTextHelpFormatter,
        help= 'Stream audio in your OS\'s local media player.')
    stream.add_argument('-b', '--bitrate', type=int, default=320, help=
        'Desired bitrate, in kbps. Can be 128 or 320. Defaults to 320.')
    stream.add_argument('-p', '--print', action='store_true', help=
        'Print stream URLs instead of opening them.')
    add_recordings_argument(stream, 'stream')

    scrape = subparsers.add_parser('scrape', formatter_class=argparse.RawTextHelpFormatter,
        help='Scrape audio metadata.')
    scrape.add_argument('-s', '--shallow', action='store_true', help=
        'When scraping an artist\'s details page, only use the recording information' + \
        'available on that page; don\'t fetch the full details for those recordings.')
    scrape.add_argument('-r', '--artist-dirs', action='store_true', help=
        'Save artist information as a directory containing individual JSON files ' + \
        'for each recording, rather than the default of a single JSON file.')
    scrape.add_argument('-j', '--save-json', action='store_true', help=
        'Save individual JSON data files for each recording instead of printing.')
    scrape.add_argument('-d', '--dest', type=str, default='.', help=
        'Destination directory for downloaded data files. Use with the -s flag.')
    add_recordings_argument(scrape, 'scrape')

    download = subparsers.add_parser('download', formatter_class=argparse.RawTextHelpFormatter,
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
