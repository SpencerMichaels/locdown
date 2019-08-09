from bs4 import BeautifulSoup
import re

from . import keys, url

A_HREF_REGEX = re.compile('\/jukebox\/([a-z]+)\/detail\/id\/(\d+)')
HREF_URL_PREFIX = 'https://www.loc.gov'
ALIAS_REGEX = re.compile('(.*) \[i.e., (.*)\]')

def fix_tag_text(s):
  s = s.strip()
  s = re.sub('\n|\t', ' ', s)
  s = re.sub('  +', ' ', s)
  s = re.sub(' ,', ',', s)
  return s

# Convert <a> tags to refs

def convert_a(a, name=keys.REF_NAME):
  ref = { keys.REF_LINK: HREF_URL_PREFIX + a['href'].strip() }
  text = fix_tag_text(a.get_text())

  match = ALIAS_REGEX.match(text)
  if match:
    ref[keys.REF_ALIAS] = match.group(1)
    ref[name] = match.group(2)
  else:
    ref[name] = text

  return ref

  #match = A_HREF_REGEX.match(a['href'])
  #if match:
  #  return { name: fix_tag_text(a.get_text()),
  #          'ref': f'{match.group(1)}/{match.group(2)}' }
  #raise ValueError('Unhandled HTML element:\n' + str(li))

# True if `item` is an artist ref or a list of artist refs
def is_artist_ref(item):
  if type(item) is list:
    return all([is_artist_ref(elem) for elem in item])
  if keys.REF_LINK in item:
    return '/artists/' in item[keys.REF_LINK]
  return False
  #return 'ref' in item and item['ref'].startswith('artists')

def li_to_key_value(li):
  key = li.find('h3').get_text().strip()

  # Single value
  p = li.find('p')
  if p:
    #return key, util.unlist1([ convert_a(a) for a in p.find_all('a', recursive=False)]) or \
    return key, [ convert_a(a) for a in p.find_all('a', recursive=False)] or \
                fix_tag_text(p.get_text())

  # List of values
  ul = li.find('ul', class_='std')
  if ul:
    lis_inner = ul.find_all('li')
    def convert_inner(inner):
      a = inner.find('a')
      return convert_a(a) if a \
          else fix_tag_text(inner.get_text())
    return key, [ convert_inner(li_inner) for li_inner in lis_inner ]

  raise ValueError('Unhandled HTML element:\n' + str(li))

def fix_title(s):
  return s.strip().replace(' :', ':')

def reformat_other_titles(titles):
  m = {}
  for pair in titles:
    title, category = pair.split('(', 1)
    category = category[:-1]
    if not category in m:
      m[category] = []
    if category == keys.OTHER_TITLE_MEDLEY_CONTENTS:
      m[category] += [ fix_title(s) for s in title.split(';') ]
    else:
      m[category].append(title.strip())
  for category in m.keys():
    m[category] = m[category]
  return m

def scrape_recording_details(html):
  soup = BeautifulSoup(html, 'html5lib')
  identifier_meta = soup.find('meta', { 'name': 'DC.identifier' })

  if not identifier_meta:
    inner_box = soup.find('div', { 'class': 'innerbox' })
    if inner_box:
      title = inner_box.find('h2').get_text()
      text = inner_box.find('p').get_text()
      raise RuntimeError(f'{title}: {text}')
    else:
      raise RuntimeError('Recording details page is in an unknown format! ' + \
                         'Check loc.gov; it may be down for maintenance.')

  link = identifier_meta['content']
  details = {
    keys.ID: url.url_to_id(link).id_,
    keys.REF_LINK: link.replace('http', 'https'),
    keys.ARTISTS: {}, 
  }

  image = soup.find('a', { 'class': 'enlarge lightbox' })
  if image:
    details[keys.IMAGE_LINK] = HREF_URL_PREFIX + image['href'].strip()

  for li in soup.select('#tab1 > ul > li'):
    key, value = li_to_key_value(li)

    # Special case to organize "other titles" a bit better
    if key == keys.OTHER_TITLES:
      value = reformat_other_titles(value)
    elif key == keys.RECORDING_TITLE:
      value = fix_title(value)

    if is_artist_ref(value):
      aliases, reals = [], []
      for entry in value:
        (aliases if keys.REF_ALIAS in entry else reals).append(entry)

      for alias in aliases:
        alias_real_name = alias.get(keys.REF_NAME)
        real = next(filter(lambda r: r.get(keys.REF_NAME) == alias_real_name, reals), None)
        if real:
          alias[keys.REF_NAME] = alias.pop(keys.REF_ALIAS, None)
          if keys.REF_ALIAS in real:
            util.log('WARNING! ref alias already exists in real') # TODO: worth handling?
          real[keys.REF_ALIAS] = alias

      details[keys.ARTISTS][key] = reals
    else:
      details[key] = value

  return details
