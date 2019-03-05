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

from protocol import PfeifferTPG26xProtocol, CommunicationError
from slave.driver import Driver, Command, _load, _typelist
from slave.types import Mapping, Stream, Float

PRESSURE_READING = {
    'Measurement data okay': '0',
    'Underrange': '1',
    'Overrange': '2',
    'Sensor error': '3',
    'Sensor off': '4',
    'No sensor': '5',
    'Identification error': '6',
}

STATUS_GAUGE_READING = {
    'Gauge cannot be turned on/off': 0,
    'Gauge turned off': 1,
    'Gauge turned on': 2
}

PRESSURE_UNIT_READING = {
    'mbar/bar': 0,
    'Torr': 1,
    'Pascal': 2
}

IDENTIFICATION_READING = {
    'Pirani Gauge or Pirani Capacitive gauge': 'TPR',
    'Cold Cathode Gauge 10^-9': 'IKR9',
    'Cold Cathode Gauge 10^-11': 'IKR11',
    'FullRange CC Gauge': 'PKR',
    'FullRange BA Gauge': 'PBR',
    'Pirani/High Pressure Gauge': 'IMR',
    'Linear Gauge': 'CMR',
    'no sensor': 'noSen',
    'no identifier': 'noid'
}

ERROR_READING = {
    'No Error': '0000',
    'Error': '1000',
    'NO HWR': '0100',
    'PAR': '0010',
    'SYN': '0001'
}

RESET_READING = {
    'No Error': 0,
    'Watchdog has responded': 1,
    'Task fail error': 2,
    'EPROM error': 3,
    'RAM error': 4,
    'EEPROM error': 5,
    'DISPLAY error': 6,
    'A/D converter error': 7,
    'Gauge 1 error': 9,
    'Gauge 1 identification error': 10,
    'Gauge 2 error': 11,
    'Gauge 2 identification error': 12
}

class Reader(object):
    def __init__(self, protocol):
        self._protocol = protocol
        
    def read(self, response_type):
        response = self._protocol.parse_response(self._protocol.get_response())
        return _load(_typelist(response_type), response)

class PfeifferTPG26xDriver(Driver):

    def __init__(self, protocol):
        super(PfeifferTPG26xDriver, self).__init__(protocol)
        assert isinstance(protocol, PfeifferTPG26xProtocol)

        self._protocol = protocol

    def query_command(self, cmd):

        response = self._protocol.query(cmd.header, ())
        response = _load(cmd.response_type, response)
        return response
        #return cmd.query(self._protocol)
        
    def get_protocol(self):
        return self._protocol

    def get_identification(self):
        cmd = Command(('TID', [Mapping(IDENTIFICATION_READING), Mapping(IDENTIFICATION_READING)]))
        return self.query_command(cmd)
    
    def turn_on_first(self):
        cmd = Command(('SEN,2,0', [Mapping(STATUS_GAUGE_READING), Mapping(STATUS_GAUGE_READING)]))
        return self.query_command(cmd)
        
    def turn_off_first(self):
        cmd = Command(('SEN,1,0', [Mapping(STATUS_GAUGE_READING), Mapping(STATUS_GAUGE_READING)]))
        return self.query_command(cmd)

    def get_error_status(self):
        cmd = Command(('ERR', Mapping(ERROR_READING)))
        return self.query_command(cmd)
    
    def reset(self):
        cmd = Command(('RES', Stream(Mapping(RESET_READING))))
        return self.query_command(cmd)
    
    def set_pressure_unit(self, unit):
        if unit == 0 or unit == 1 or unit == 2:
            cmd = Command(('UNI,'+str(unit), Mapping(PRESSURE_UNIT_READING)))
            return self.query_command(cmd)
        
        raise ValueError('Wrong unit')
    
    def get_pressure_measurement(self, gauge = 1):
        if(gauge == 1 or gauge == 2):
            cmd = Command(('PR'+str(gauge), [Mapping(PRESSURE_READING), Float]))
            return self.query_command(cmd)
        
        raise ValueError('Wrong gauge')

    def get_pressure(self):
        return self.get_pressure_measurement()[1]

    # Note that this method should only be called after an
    # `start_continuous_measurement`
    def get_continuous_measurement(self):
        
        reader = Reader(self._protocol)
        return reader.read([Mapping(PRESSURE_READING), Float, Mapping(PRESSURE_READING), Float])
    
    # Even though there is no necessity to explicitly stop the
    # continuous measurement, the buffer might be filled with 
    # those measurements, and the next cmd will not get an <ACK>
    # So there is a stopping method.
    def start_continuous_measurement(self, mode=1):
        if mode not in [0, 1, 2]:
            raise ValueError('Wrong mode')

        cmd = Command(('COM,' + str(mode), [Mapping(PRESSURE_READING), Float, Mapping(PRESSURE_READING), Float]))
        # we have to skip the next enquiry (so no <ENQ> will be send after the receiving <ACK>)
        # why?
        # after sending COM, the gauge will send continous data to us
        # as long as we do not interrupt him with another cmd, and since
        # <ENQ> is a cmd, we have to omit this.
        self._protocol.skipNextEnquiry()
        return self.query_command(cmd)

    def stop_continuous_measurement(self):
        # Fire any cmd, in order to stop measurement
        try:
            self.reset()
        except CommunicationError as e:
            # ignore this error... since we're in COM, we will not receive an <ACK>
            pass
                
        self._protocol.clear()