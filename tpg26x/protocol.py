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

from e21_util.interface import Loggable
from e21_util.lock import InterProcessTransportLock
from e21_util.error import CommunicationError
from e21_util.serial_connection import AbstractTransport, SerialTimeoutException

class PfeifferTPG26xProtocol(Loggable):

    def __init__(self, transport, logger):
        super(PfeifferTPG26xProtocol, self).__init__(logger)

        assert isinstance(transport, AbstractTransport)
        self._transport = transport
        
        self.encoding = "ascii"
        self.responseTerminal = "\r\n"
        self.messageTerminal = "\r\n"
        self.responseDataSeparator = ","
        self.skipEnquiry = False

    def reset(self):
        self._transport.write(b'\x03')

    def create_message(self, header, *data):
        msg = []
        msg.append(header)
        msg.extend(data)
        msg.append(self.messageTerminal)
        return ''.join(msg).encode(self.encoding)

    def clear(self):
        with self._transport:
            # Send <CR><LF>
            # this should stop always the continuous measurement
            self._logger.debug("Clearing message buffer...")
            self._transport.write(b'\x0D\x0A')
            try:
                while True:
                    self._transport.read_bytes(32)
            except SerialTimeoutException:
                return

    def skipNextEnquiry(self, skip=True):
        self.skipEnquiry = skip
    
    def enquiry(self):
        if not self.skipEnquiry:
                self._transport.write(b'\x05')

        self.skipEnquiry = False

    def get_response(self):
        try:
            resp = self._transport.read_until(self.responseTerminal.encode(self.encoding))
            self._logger.debug("Received {}".format(repr(resp)))
            # now remove the response terminal
            return resp[:-len(self.responseTerminal)]
        except SerialTimeoutException:
            raise CommunicationError("Received a timeout")

    def parse_response(self, response):
        return response.decode(self.encoding).split(self.responseDataSeparator)

    def is_acknowledged(self):
        response = self.get_response()

        if self.is_nack(response):
            raise CommunicationError("Acknowledgement error! Negative Acknowledgement received")

        if not self.is_ack(response):
            raise CommunicationError("Acknowledgement error! No acknowledgement was sent back from gauge")

    def is_ack(self, response):
        return response == b'\x06'
    
    def is_nack(self, response):
        return response == b'\x15'
            
    def query(self, header, *data):
        with self._transport:
            message = self.create_message(header, *data)
            self._logger.debug('Query: %s', repr(message))

            self._transport.write(message)
            self.is_acknowledged()
            self.enquiry()
            response = self.get_response()

            self._logger.debug('Response: %s', repr(response))
            return self.parse_response(response)

    def write(self, transport, header, *data):
        return self.query(transport, header, *data)
