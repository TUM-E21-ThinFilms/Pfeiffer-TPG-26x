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

import slave

import e21_util
from e21_util.lock import InterProcessTransportLock
from e21_util.error import CommunicationError

from slave.protocol import Protocol
from slave.transport import Timeout

class PfeifferTPG26xProtocol(Protocol):

    def __init__(self, logger):
        self.encoding = "ascii"
        self.responseTerminal = "\r\n"
        self.messageTerminal = "\r\n"
        self.responseDataSeparator = ","
        self.skipEnquiry = False
        self.logger = logger

    def reset(self, transport):
        transport.write(b'\x03')
        
    def set_logger(self, logger):
        self.logger = logger

    def create_message(self, header, *data):
        msg = []
        msg.append(header)
        msg.extend(data)
        msg.append(self.messageTerminal)
        return ''.join(msg).encode(self.encoding)

    def clear(self, transport):
        with InterProcessTransportLock(transport):
            # Send <CR><LF>
            # this should stop always the continous measurement
            self.logger.debug("Clearing message buffer...")
            transport.__write__(b'\x0D\x0A')
            try:
                while True:
                    transport.read_bytes(32)
            except slave.transport.Timeout:
                return

    def skipNextEnquiry(self, skip=True):
        self.skipEnquiry = skip
    
    def enquiry(self, transport):
        if not self.skipEnquiry: 
            transport.write(b'\x05')
        
        self.skipEnquiry = False

    def get_response(self, transport):
        try:
            return transport.read_until(self.responseTerminal.encode(self.encoding))
        except slave.transport.Timeout:
            raise CommunicationError("Received a timeout")

    def parse_response(self, response):
        return response.decode(self.encoding).split(self.responseDataSeparator)

    def is_acknowledged(self, transport):
        response = self.get_response(transport)

        if self.is_nack(response):
            raise CommunicationError("Acknowledgement error! Negative Acknowledgement received")
        if not self.is_ack(response):
            self.logger.debug("Received: \"%s\"", repr(response))
            raise CommunicationError("Acknowledgement error! No acknowledgement was sent back from gauge")

    def is_ack(self, response):
        return response == b'\x06'
    
    def is_nack(self, response):
        return response == b'\x15'
            
    def query(self, transport, header, *data):
        with InterProcessTransportLock(transport):
            message = self.create_message(header, *data)
            self.logger.debug('Query: %s', repr(message))
            with transport:
                transport.write(message)
                self.is_acknowledged(transport)
                self.enquiry(transport)
                response = self.get_response(transport)
            self.logger.debug('Response: %s', repr(response))
            return self.parse_response(response)

    def write(self, transport, header, *data):
        return self.query(transport, header, *data)
