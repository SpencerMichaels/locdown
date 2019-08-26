from mutagen import id3, mp3

import mimetypes

from ..jukebox import keys
from . import tagmaker

async def tag(path, metadata, session=None):
  audio = mp3.MP3(path)
  audio.tags = id3.ID3()

  for maker in tagmaker.tag_makers:
    tag = maker(metadata)
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
