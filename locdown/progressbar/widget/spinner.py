from itertools import cycle

class Spinner:

  CHARS_SIMPLE = '|/-\\'
  # See https://www.fileformat.info/info/unicode/block/braille_patterns/list.htm
  CHARS_DOTS_LOOP = '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'

  CHAR_CHECK = '✓'

  def __init__(self, period=1, chars=CHARS_DOTS_LOOP, char_done=CHAR_CHECK):
    self.update_interval = period/len(chars)
    self.chars = cycle(chars)
    self.char_done = char_done

  def __call__(self, width, state):
    if state.num_done == state.num_total:
      return self.char_done
    return next(self.chars)
