from enum import Enum

class Padding(Enum):
  SPACES = ''
  ZEROS = '0'
  NONE = None

from .bar import Bar
from .fraction import Fraction
from .percent import Percent
from .spinner import Spinner
