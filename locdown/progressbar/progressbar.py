from enum import Enum
import shutil

class ProgressBar():
  class FormatDirection(Enum):
    LEFT_TO_RIGHT = 1
    RIGHT_TO_LEFT = -1

  @staticmethod
  def _validate_fmt(fmt, widgets):
    if fmt and fmt.count('%s') != len(widgets):
      raise ValueError('Number of widgets must match the number of %s specifiers in `fmt`.')
    elif not fmt:
      fmt = ' '.join(len(widgets) * ['%s'])
    return fmt, widgets

  @staticmethod
  def _format_widgets(state, width, fmt, widgets, direction):
    literals = fmt.split('%s')
    result = ''

    range_ = range(0, len(widgets))
    if direction == ProgressBar.FormatDirection.RIGHT_TO_LEFT:
      range_ = reversed(range_)

    for i in range_:
      result += literals[i]
      result += widgets[i](width - len(result), state)
    result += literals[0 if direction == ProgressBar.FormatDirection.RIGHT_TO_LEFT else -1]
    return result

  def __init__(self, left=[], right=[], left_fmt=None, right_fmt=None,
      width=None, direction=FormatDirection.LEFT_TO_RIGHT):
    self.left_fmt, self.left_widgets = self._validate_fmt(left_fmt, left)
    self.right_fmt, self.right_widgets = self._validate_fmt(right_fmt, right)
    self.width = width
    self.direction = direction

    intervals = [ w.update_interval for w in (left+right) if hasattr(w, 'update_interval') ]
    self.update_interval = min(intervals) if intervals else None

  def __call__(self, state):
    width = self.width or shutil.get_terminal_size((80, 1)).columns

    def format_left(width):
      return self._format_widgets(state, width, self.left_fmt, self.left_widgets,
          direction=ProgressBar.FormatDirection.LEFT_TO_RIGHT)

    def format_right(width):
      return self._format_widgets(state, width, self.right_fmt, self.right_widgets,
          direction=ProgressBar.FormatDirection.RIGHT_TO_LEFT)

    if self.direction == self.FormatDirection.LEFT_TO_RIGHT:
      left = format_left(width)
      right = format_right(width - len(left))
    else:
      right = format_right(width)
      left = format_left(width - len(right))

    pad = width - len(left) - len(right)
    return left + ' '*pad + right
