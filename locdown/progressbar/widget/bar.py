import math

class Bar:

  CHARS_SIMPLE = '≡> '
  CHARS_HIGHRES = '█▉▊▋▌▍▎▏ '

  CAP_CHARS_DEFAULT = '[]' # Must be len 2

  def __init__(self, max_width=None, chars=CHARS_HIGHRES, caps=CAP_CHARS_DEFAULT):
    if caps and len(caps) != 2:
      raise ValueError('`caps` parameter must be exactly 2 chars long')
    if not chars or len(chars) < 2:
      raise ValueError('`chars` parameter must be at least 2 chars long')

    self.chars = chars
    self.chars_midpoint = chars[1:-1]
    self.caps = caps
    self.max_width = max_width

  def __call__(self, width, state):
    width = min(self.max_width, width) if self.max_width else width
    bar_width = width-2 if self.caps else width
    threshold = bar_width * state.num_done / state.num_total

    threshold_lower = math.floor(threshold)
    threshold_upper = threshold_lower + 1

    bar = self.caps[0] if self.caps else ''
    bar += self.chars[0] * threshold_lower
    if state.num_done < state.num_total:
      if state.num_done > 0 and self.chars_midpoint:
        index = math.floor((threshold % 1) * len(self.chars_midpoint))
        bar += self.chars_midpoint[-index-1]
      else:
        bar += self.chars[-1]
    bar += self.chars[-1] * (bar_width - threshold_upper)
    bar += self.caps[-1] if self.caps else ''

    return bar
