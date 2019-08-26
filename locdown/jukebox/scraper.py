from bs4 import BeautifulSoup
import asyncio
import functools, math, re

from . import keys, url

A_HREF_REGEX = re.compile('\/jukebox\/([a-z]+)\/detail\/id\/(\d+)')
HREF_URL_PREFIX = 'https://www.loc.gov'
ALIAS_REGEX = re.compile('(.*) \[i.e., (.*)\]')
ARTIST_RESULTS_REGEX = re.compile('Results: (\d+)-(\d+) of (\d+)')

def get_tag_text(tag):
  s = tag.get_text().strip()
  s = re.sub('\n|\t', ' ', s)
  s = re.sub('  +', ' ', s)
  s = re.sub(' ,', ',', s)
  return s

# Convert <a> tags to refs

def convert_a(a, name=keys.REF_NAME):
  ref = { keys.REF_LINK: HREF_URL_PREFIX + a['href'].strip() }
  text = get_tag_text(a)

  match = ALIAS_REGEX.match(text)
  if match:
    ref[keys.REF_ALIAS] = match.group(1)
    ref[name] = match.group(2)
  else:
    ref[name] = text

  return ref

# True if `item` is an artist ref or a list of artist refs
def is_artist_ref(item):
  if type(item) is list:
    return all([is_artist_ref(elem) for elem in item])
  if keys.REF_LINK in item:
    return '/artists/' in item[keys.REF_LINK]
  return False

def li_to_key_value(li):
  key = li.find('h3').get_text().strip()

  # Single value
  p = li.find('p')
  if p:
    return key, [ convert_a(a) for a in p.find_all('a', recursive=False)] or \
                  get_tag_text(p)

  # List of values
  ul = li.find('ul', class_='std')
  if ul:
    lis_inner = ul.find_all('li')
    def convert_inner(inner):
      a = inner.find('a')
      return convert_a(a) if a \
          else get_tag_text(inner)
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

def raise_page_format_exception(url_):
  raise RuntimeError(f'The page `{url_}` is in an unrecognized format! ' + \
                     'Check loc.gov; it may be down for maintenance.')

async def get_soup(session, url_):
  async with session.get(url_) as response:
    data = await response.read()
    html = data.decode('utf-8', errors='ignore')
    return BeautifulSoup(html, 'html5lib')

def do_page_structure_sanity_check(soup):
  # The DC.identifier meta tag is found on both recording and artist details pages
  # If it's not there, the page is not structured as we expect it to be.
  if not soup.find('meta', { 'name': 'DC.identifier' }):
    # Try to extract the error message provided by the page
    inner_box = soup.find('div', { 'class': 'innerbox' })
    if inner_box:
      title = inner_box.find('h2').get_text()
      text = inner_box.find('p').get_text()
      raise RuntimeError(f'{title}: {text}')
    else:
      # If all else fails, present a generic error
      raise_page_format_exception(url_)

async def scrape_recording(session, id_):
  url_ = url.id_to_details_url(id_, 'recordings')
  soup = await get_soup(session, url_)

  do_page_structure_sanity_check(soup)

  details = {
    keys.ID: id_,
    keys.REF_LINK: url_,
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
          real[keys.REF_ALIAS] = alias

      details[keys.ARTISTS][key] = reals
    else:
      details[key] = value

  return details

async def scrape_artist(session, id_, shallow=False):
  url_ = url.id_to_details_url(id_, 'artists')
  soup = await get_soup(session, url_)

  do_page_structure_sanity_check(soup)

  metadata = {
      keys.ID: id_,
      keys.REF_LINK: url_,
  }

  name_h1 = soup.select_one('#page_head > h1')
  if not name_h1:
    raise_page_format_exception(url_)
  else:
    metadata[keys.REF_NAME] = get_tag_text(name_h1)

  desc_p = soup.find('div', { 'class': 'innerbox' }).find('p', { 'class': '' })
  desc = get_tag_text(desc_p)
  if desc:
    metadata[keys.DESCRPTION] = desc

  n_results_div = soup.find('div', { 'class': 'n_results' })
  if not n_results_div:
    return metadata # No recordings for this artist!

  results_text = get_tag_text(n_results_div)

  match = ARTIST_RESULTS_REGEX.match(results_text)
  if not match:
    raise_page_format_exception(url_)

  result_first, result_last, result_max = map(int, match.groups())
  num_pages = math.ceil(result_max/(result_last - result_first + 1))

  async def scrape_artist_recordings_from_soup(soup):
    table = soup.find('table', { 'id': 'artist-takes' })
    col_names = [ get_tag_text(h) for h in table.select('tr > th') ]
    rows = table.select('tbody > tr')

    async def get_row_metadata(row):
      cols = row.find_all('td')
      link = HREF_URL_PREFIX + cols[2].find('a')['href'].strip()
      id_ = int(link.split('/')[-1])

      if not shallow:
        return await scrape_recording(session, id_)
      else:
        row_metadata = {
            keys.ID: id_,
            keys.REF_LINK: link,
        }

        img_src = cols[0].select_one('div > div > img')['src']
        if img_src != '/jukebox/images/album_default.jpg': # No image available
          row_metadata[keys.IMAGE_LINK] = HREF_URL_PREFIX + img_src

        for i, col in enumerate(cols[1:]):
          row_metadata[col_names[i+1]] = get_tag_text(col)

        return row_metadata

    return await asyncio.gather(*map(get_row_metadata, rows))

  async def scrape_artist_recordings(page_num):
    soup = await get_soup(session, f'{url_}?page={page_num}')
    return await scrape_artist_recordings_from_soup(soup)

  # Download and scrape pages 2+ only; we already downloaded page 1 above
  tasks = map(scrape_artist_recordings, range(2, num_pages+1))
  pages = await asyncio.gather(*tasks)

  metadata[keys.RECORDINGS] = functools.reduce(
      lambda accum, recordings: accum + recordings,
      pages, await scrape_artist_recordings_from_soup(soup))

  return metadata
