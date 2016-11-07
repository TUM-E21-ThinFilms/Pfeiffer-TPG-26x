# Copyright (C) 2016, see AUTHORS.md
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from slave.types import Range
import sys, random

class Percent(Range):

    def __init__(self, precision=0, number_of_digits=6, min=0, max=100, *args, **kw):
        super(Percent, self).__init__(*args, **kw)

        self._precision = int(precision)
        self._number_of_digits = int(number_of_digits)

    def __convert__(self, value):
        return float(value)

    def __Percent_to_String__(self, input_percent=0):

        if (input_percent > 100):  # Check whether input is valid
            print ("Error, percentage > 100!")
            return ''

        output_str = str(input_percent)
        length = len(output_str)
        dot_position = output_str.find('.')
        if dot_position == -1:
            dot_position = length - 1
        if (length > (self._precision + 4 + dot_position - 2)):
            print ("Error, input too precise!")
            return ''

        output_str = output_str.replace('.', '')  # Remove the dot

        # '{0:<034.2f}'.format(45.2123): Reminder for integer to string formatting

        output_str = (
        '{0:>0' + str(self._number_of_digits + length - self._precision - 4 - dot_position + 2) + '}').format(
            output_str)  # Fill out with '0' on the left
        output_str = ('{0:<0' + str(self._number_of_digits) + '}').format(output_str)  # Fill out with '0' on the right
        return output_str

    def __String_to_Percent__(self, position_input):
        # """Forms the percentage value out of a string"""
        return float(position_input) / pow(10, int(self._precision) + 1)

    def dump(self, value):
        return self.__Percent_to_String__(value)

    def load(self, value):
        return self.__String_to_Percent__(value)

    def simulate(self):
        min_ = sys.float_info.min if self._min is None else self._min
        max_ = sys.float_info.max if self._max is None else self._max
        return random.uniform(min_, max_)