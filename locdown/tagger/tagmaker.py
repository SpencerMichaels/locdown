from mutagen import id3

from .. import util
from ..jukebox import keys

def _tag_transform(m, tag, f, *keys):
  for key in keys:
    if not key in m:
      return None
    m = m.get(key)
  if f:
    m = f(m)
  return tag(text=m)

def _tag(m, tag, *keys):
  return _tag_transform(m, tag, None, *keys)

def _title_text(metadata):
  title = metadata.get(keys.RECORDING_TITLE)
  if keys.OTHER_TITLES in metadata:
    other_titles = metadata.get(keys.OTHER_TITLES)
    if keys.OTHER_TITLE_SUBTITLE in other_titles:
      subtitle = '; '.join(other_titles.get(keys.OTHER_TITLE_SUBTITLE))
      title += f' ({subtitle})'

  # If there is more than one take available, add the take number to disambiguate
  if keys.RELATED_TAKES in metadata and keys.MATRIX_AND_TAKE_NUMBER in metadata:
    take_number = metadata.get(keys.MATRIX_AND_TAKE_NUMBER).split('/')[1]
    title += f' (take {take_number})'

  return title

def _alias(performer):
  name = performer.get(keys.REF_NAME)
  alias = performer.get(keys.REF_ALIAS)
  if alias:
    aname = alias if type(alias) == str \
        else alias.get(keys.REF_NAME)
    name = f'{aname} ({name})'
  return name

def _performer_list(metadata):
  artists = metadata.get(keys.ARTISTS)
  performers = []

  # Sometimes the LoCJ will list every musician in an orchestra *individually*,
  # which is obviously not very useful for sorting by performer. Here we
  # heuristically attempt to determine the most relevant listing of artists.
  # If a group name is available, we use that; second, we try vocalists,
  # and only if that fails do we use a full listing of performers.
  groups = [ role for role in artists.keys() if 'group' in role ]
  vocals = [ role for role in artists.keys() if 'vocal' in role or 'Speaker' in role ]

  if groups:
    performers = [ artists.get(group) for group in groups ]
  elif vocals:
    performers = [ artists.get(vocal) for vocal in vocals ]
  else:
    performers = [ people for role, people in artists.items() \
                   if role not in keys.NON_PERFORMING_ARTISTS ]

  return ', '.join([ _alias(performer) for performer in util.flatten(performers) ])

def title(metadata):
  return id3.TIT2(text=_title_text(metadata))

def date(metadata):
  return _tag(metadata, id3.TDRC, keys.RECORDING_DATE)

def language(metadata):
  return _tag(metadata, id3.TLAN, keys.LANGUAGE)

def length(metadata):
  return _tag(metadata, id3.TLEN, keys.DURATION)

def composer(metadata):
  return _tag_transform(metadata, id3.TCOM,
      lambda artists: artists[0][keys.REF_NAME],
      keys.ARTISTS, keys.ARTIST_COMPOSER)

def lyricist(metadata):
  return _tag_transform(metadata, id3.TEXT,
      lambda artists: artists[0][keys.REF_NAME],
      keys.ARTISTS, keys.ARTIST_LYRICIST)

def album(metadata):
  album = metadata.get(keys.LABEL_NAME_AND_NUMBER)
  return id3.TALB(text=album)

def lead_performer(metadata):
  return id3.TPE1(text=_performer_list(metadata)) # Remove the trailing semicolon

def track_number(metadata):
  return _tag_transform(metadata, id3.TRCK, lambda i: str(i), keys.ID)

def genre(metadata):
  return _tag(metadata, id3.TCON, keys.GENRES)

def comments(metadata):
  if keys.NOTES in metadata:
    return id3.COMM(text=metadata[keys.NOTES], desc='Notes', lang='eng')
  return None

def publisher(metadata):
  return _tag_transform(metadata, id3.TPUB,
      lambda s: s.split(' ')[0], keys.LABEL_NAME_AND_NUMBER)

def fix_filename(filename):
  filename = filename.replace(':', ' -') # best to keep colons out of filenames
  filename = filename.replace('/', ', ') # DEFINITELY remove slashes
  return filename

def filename(metadata, artist_metadata=None):
  filename = f'{metadata.get(keys.ID)} - {_performer_list(metadata)} - {_title_text(metadata)}' \
    if keys.ARTISTS in metadata \
    else f'{metadata.get(keys.ID)} - {_alias(artist_metadata)} - {metadata.get(keys.TITLE)}'
  return fix_filename(filename)

def dirname(metadata):
  filename = f'{metadata.get(keys.ID)} - {_performer_list(metadata)}' \
    if keys.ARTISTS in metadata \
    else f'{metadata.get(keys.ID)} - {_alias(metadata)}' # shallow
  return fix_filename(filename)

tag_makers = [
    title,
    date,
    language,
    length,
    composer,
    lyricist,
    album,
    lead_performer,
    publisher,
    track_number,
    genre,
    comments,
]
