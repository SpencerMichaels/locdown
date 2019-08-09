from mutagen import id3, mp3

import mimetypes

from .jukebox import keys
from . import util

def make_transform(m, tag, f, *keys):
  for key in keys:
    if not key in m:
      return None
    m = m.get(key)
  if f:
    m = f(m)
  return tag(text=m)

def make(m, tag, *keys):
  return make_transform(m, tag, None, *keys)

def make_title_text(metadata):
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

def make_performer_list(metadata):
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

  names = []
  for performer in util.flatten(performers):
    name = performer.get(keys.REF_NAME)
    alias = performer.get(keys.REF_ALIAS)
    if alias:
      name = f'{alias.get(keys.REF_NAME)} ({name})'
    names.append(name)

  return ', '.join(names)

def make_title(metadata):
  return id3.TIT2(text=make_title_text(metadata))

def make_date(metadata):
  return make(metadata, id3.TDRC, keys.RECORDING_DATE)

def make_language(metadata):
  return make(metadata, id3.TLAN, keys.LANGUAGE)

def make_length(metadata):
  return make(metadata, id3.TLEN, keys.DURATION)

def make_composer(metadata):
  return make_transform(metadata, id3.TCOM,
      lambda artists: artists[0][keys.REF_NAME],
      keys.ARTISTS, keys.ARTIST_COMPOSER)

def make_lyricist(metadata):
  return make_transform(metadata, id3.TEXT,
      lambda artists: artists[0][keys.REF_NAME],
      keys.ARTISTS, keys.ARTIST_LYRICIST)

def make_album(metadata):
  # The concept of "albums" doesn't really make sense for records
  album = metadata.get(keys.LABEL_NAME_AND_NUMBER)

  #album = f'Library of Congress Jukebox #{metadata.get(keys.ID)}'

  #label_name_num = metadata.get(keys.LABEL_NAME_AND_NUMBER)
  #if label_name_num:
  #  album += f': {label_name_num}'
  #  matrix_num = metadata.get(keys.MATRIX_AND_TAKE_NUMBER)
  #  if matrix_num:
  #    album += f' {matrix_num}'

  return id3.TALB(text=album)

def make_lead_performer(metadata):
  #s = ''
  #for role, artists in metadata.get(keys.ARTISTS).items():
  #  # Composer, lyricist and conductor are artists, but not performers
  #  if role not in keys.NON_PERFORMING_ARTISTS:
  #    s += ', '.join([a[keys.REF_NAME] for a in artists])
  #    s += f' ({role}); '
  return id3.TPE1(text=make_performer_list(metadata)) # Remove the trailing semicolon

def make_track_number(metadata):
  # TODO: Does this make sense? Jukebox ID is embedded in the title
  return make_transform(metadata, id3.TRCK, lambda i: str(i), keys.ID)

def make_genre(metadata):
  return make(metadata, id3.TCON, keys.GENRES)

def make_comments(metadata):
  if keys.NOTES in metadata:
    return id3.COMM(text=metadata[keys.NOTES], desc='Notes', lang='eng')
  return None

def make_publisher(metadata):
  return make_transform(metadata, id3.TPUB,
      lambda s: s.split(' ')[0], keys.LABEL_NAME_AND_NUMBER)

def make_filename(metadata):
  title_text = make_title_text(metadata).replace(':', ' -') # best to keep colons out of filenames
  filename = f'{metadata.get(keys.ID)} - {make_performer_list(metadata)} - {title_text}'
  return filename


TAGGERS = [
    make_title,
    make_date,
    make_language,
    make_length,
    make_composer,
    make_lyricist,
    make_album,
    make_lead_performer,
    make_publisher,
    make_track_number,
    make_genre,
    make_comments,
]

async def tag(path, metadata, session=None):
  audio = mp3.MP3(path)
  audio.tags = id3.ID3()

  for tagger in TAGGERS:
    tag = tagger(metadata)
    if tag:
      audio.tags.add(tag)

  if keys.IMAGE_LINK in metadata:
    url = metadata.get(keys.IMAGE_LINK)
    if session:
      mime, _ = mimetypes.guess_type(url)
      async with session.get(url) as response:
        data = await response.read()
        audio.tags.add(id3.APIC(encoding=id3.Encoding.UTF8, mime=mime, type=id3.PictureType.COVER_FRONT, desc='Front cover', data=data))
    else:
      # In practice, this is unsupported by most media players
      # But there's no reason not to do it
      audio.tags.add(id3.APIC(data=url, mime='-->'))

  audio.save()
