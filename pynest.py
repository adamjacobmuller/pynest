import urllib2
import urllib
import json
import pprint
import time
import sys


def j_dump(data):
    print json.dumps(data, indent=4)


class NestThermostat():
    def __init__(self, structure, thermostat, data, serial):
        self.name = thermostat['name']
        self.temperature = thermostat['current_temperature']
        self.fan = thermostat['hvac_fan_state']
        self.cool = thermostat['hvac_ac_state']
        self.heat = thermostat['hvac_heater_state']
        self.serial = serial
        self.structure = structure
        self.track = data['track'][serial]
        self.shared = data['shared'][serial]
        self.device = data['device'][serial]

    def __repr__(self):
        return "<NestThermostat %s / Serial %s [ Temperature: %s / Heat: %s / Cool: %s / Fan: %s ]>" % (
            self.name,
            self.serial,
            self.temperature,
            self.heat,
            self.cool,
            self.fan
        )

    def set_thermostat_shared(self, **kwargs):
        return self.structure.account._make_request("/v2/put/shared." + self.serial, data = kwargs)

    def set_thermostat_device(self, **kwargs):
        return self.structure.account._make_request("/v2/put/device." + self.serial, data = kwargs)

    def set_temperature(self, temperature):
        # temp in c
        return self.set_thermostat_shared(target_change_pending = True, target_temperature = int(temperature))

    def set_mode(self, mode):
        # heat|cool|range|off
        return self.set_thermostat_shared(target_temperature_type = mode)

    def set_fan_timer_timeout(self, timeout):
        # epoch seconds, when to turn off fan
        return self.set_thermostat_device(fan_timer_timeout = int(timeout))

    def set_fan_timer_duration(self, duration):
        # seconds
        return self.set_thermostat_device(fan_timer_duration = int(duration))

    def set_fan_duty_cycle(self, duty_cycle):
        # seconds per hour
        return self.set_thermostat_device(fan_duty_cycle = duty_cycle)

    def set_fan_duty_range(self, start, end):
        # seconds
        return self.set_thermostat_device(fan_duty_start_time = int(start), fan_duty_end_time = int(end))

    def set_fan_mode(self, mode):
        # on|auto|duty-cycle
        return self.set_thermostat_device(fan_mode = mode)


class NestStructure():
    def __init__(self, account, structure, data, uuid):
        self.account = account
        self.name = structure['name']
        self.away = structure['away']
        self.uuid = uuid
        self.thermostat_list = []
        for device in structure['devices']:
            serial = device[7:]
            self.thermostat_list.append(NestThermostat(self, data['shared'][serial], data, serial))

    def set_structure(self, **kwargs):
        return self.account._make_request("/v2/put/structure." + self.uuid, data = kwargs)

    def set_away(self, away = True):
        return self.set_structure(away_timestamp=time.time(), away = away, away_setter = 0)

    def set_back(self):
        return self.set_structure(away_timestamp=time.time(), away = False, away_setter = 0)

    def __repr__(self):
        return "<NestStructure %s / UUID %s [ Away: %s ]>" % (
            self.name,
            self.uuid,
            self.away
        )

    def thermostats(self, **kwargs):
        try:
            if kwargs['all'] is True:
                return self.thermostat_list
        except KeyError:
            pass
        m_thermostats = []
        for thermostat in self.thermostat_list:
            match = True
            for arg in kwargs:
                if getattr(thermostat, arg) != kwargs[arg]:
                    match = False
                    break
            if match is True:
                m_thermostats.append(thermostat)
        return m_thermostats

    def thermostat(self, **kwargs):
        for thermostat in self.thermostat_list:
            match = True
            for arg in kwargs:
                if getattr(thermostat, arg) != kwargs[arg]:
                    match = False
                    break
            if match is True:
                return thermostat


class NestAccount():
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.res = None
        self.login()
        self.load()

    def login(self):
        data = urllib.urlencode({"username": self.username, "password": self.password})

        req = urllib2.Request("https://home.nest.com/user/login",
                              data,
                              {"user-agent": "pynest (pynest@adam.gs) CFNetwork/548.0.4"})

        res = urllib2.urlopen(req)

        self.res = json.load(res)

        self.transport_url = self.res["urls"]["transport_url"]
        self.access_token = self.res["access_token"]
        self.userid = self.res["userid"]

    def structures(self, **kwargs):
        try:
            if kwargs['all'] is True:
                return self.structure_list
        except KeyError:
            pass
        m_structures = []
        for structure in self.structure_list:
            match = True
            for arg in kwargs:
                if getattr(structure, arg) != kwargs[arg]:
                    match = False
                    break
            if match is True:
                m_structures.append(structure)
        return m_structures

    def structure(self, **kwargs):
        for structure in self.structure_list:
            match = True
            for arg in kwargs:
                if getattr(structure, arg) != kwargs[arg]:
                    match = False
                    break
            if match is True:
                return structure

    def load(self):
        req = self._make_request("/v2/mobile/user.%s" % self.userid)
        self.structure_list = []
        for structure in req['structure']:
            self.structure_list.append(NestStructure(self, req['structure'][structure], req, uuid = structure))

    def _make_request(self, url, data = None, headers = {}):
        if self.res is None:
            self.login()
        headers["user-agent"] = "Nest/1.1.0.10 CFNetwork/548.0.4"
        headers["Authorization"] = "Basic %s" % self.access_token
        headers["X-nl-user-id"] = self.userid
        headers["X-nl-protocol-version"] = "1"

        if data is not None and not isinstance(data, str):
            data = json.dumps(data)

        full_url = "%s%s" % (self.transport_url, url)

        req = urllib2.Request(full_url,
                              data = data,
                              headers = headers
                              )

        response = urllib2.urlopen(req)
        response_info = response.info()

        content_type = response_info.getheader("Content-Type")
        content_length = int(response_info.getheader("Content-Length"))

        if content_length == 0:
            return True

        if content_type == "application/json":
            return json.load(response)

        return response.read()

    def __repr__(self):
        return "<NestAccount %s / UserID %s>" % (self.username, self.userid)


def get_args():
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-s", "--structure", dest="structures", action="append", default = [])
    parser.add_option("-t", "--thermostat", dest="thermostats", action="append", default = [])
    parser.add_option("-u", "--all-thermostats", dest="all_thermostats", action="store_true", default = False)
    parser.add_option("-w", "--all-structures", dest="all_structures", action="store_true", default = False)
    parser.add_option("-d", "--debug", dest="debug", action="store_true", default = False)
    parser.add_option("-l", "--list", dest="list", action="store_true", default = False)

    return parser.parse_args()


def list_to_dicts(items):
    r_list = []
    for item in items:
        r_dict = {}
        for s_item in item.split(","):
            (k, v) = item.split("=", 2)
            r_dict[k] = v
        r_list.append(r_dict)
    return r_list

if __name__ == "__main__":
    (options, args) = get_args()
    if options.debug:
        handler = urllib2.HTTPSHandler(debuglevel=1)
        handler.set_http_debuglevel(1)
        opener = urllib2.build_opener(handler)
        urllib2.install_opener(opener)

    settings = json.load(open("pynest.json", "r"))

    nest = NestAccount(settings['username'], settings['password'])

    if options.list:
        print nest
        for structure in nest.structures():
            print "    %s" % structure
            for thermostat in structure.thermostats():
                print "        %s" % thermostat
        sys.exit(0)

    if options.all_structures:
        control = "structures"
        structures = [ {'all': True}]
    elif len(options.structures) > 0:
        control = "structures"
        structures = list_to_dicts(options.structures)

    if options.all_thermostats:
        control = "thermostats"
        thermostats = [ {'all': True}]
    elif len(options.thermostats) > 0:
        control = "thermostats"
        thermostats = list_to_dicts(options.thermostats)

    thermostat_command_map = {
        'temperature': ( 'set_temperature', 1),
        'fan-duty-cycle': ( 'set_fan_duty_cycle', 1),
        'fan-mode': ( 'set_fan_mode', 1),
        'fan-duty-range': ( 'set_fan_duty_range', 2),
        'fan-duty-cycle': ( 'set_fan_duty_cycle', 1),
        'fan-timer-duration': ( 'set_fan_timer_duration', 1),
        'fan-timer-timeout': ( 'set_fan_timer_timeout', 1),
        'mode': ( 'set_mode', 1)
    }

    structure_command_map = {
        'away': ( 'set_away', 0),
        'back': ( 'set_back', 0)
    }

    nest_controls = []
    if control == "thermostats":
        command_map = thermostat_command_map
        for structure_kwargs in structures:
            for structure in nest.structures(**structure_kwargs):
                for thermostat_kwargs in thermostats:
                    for thermostat in structure.thermostats(**thermostat_kwargs):
                        nest_controls.append(thermostat)
    if control == "structures":
        command_map = structure_command_map
        for structure_kwargs in structures:
            for structure in nest.structures(**structure_kwargs):
                nest_controls.append(structure)

    print "Controlling:"
    for nest_control in nest_controls:
        print "    %s" % nest_control

    args_s = list(args)
    for nest_control in nest_controls:
        args = list(args_s)
        while len(args) > 0:
            command = args.pop(0)
            function = command_map[command]
            method = getattr(nest_control, function[0])
            function_args = []
            for i in range(0, function[1]):
                function_args.append(args.pop(0))

            method(*function_args)
            print "%s(%s)" % (method, function_args)
