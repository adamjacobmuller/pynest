import urllib2
import urllib
import json
import pprint
import time
import sys
import os

from sh import rrdtool


def j_dump(data):
    print json.dumps(data, indent=4)


def string_to_bool(string):
    stbmap = {
        'true': True,
        'false': False,
        'on': True,
        'off': False
    }
    try:
        return stbmap[string.lower()]
    except KeyError:
        raise Exception("unable to interpret %s as a boolean value expecting (on|off|true|false)" % string)


class NothingToDo(Exception):
    pass


def rrdupdate(base, filename, values):
    filename = '%s/%s.rrd' % ( base, filename)
    if os.path.exists(filename) is False:
        rras = [
            "RRA:AVERAGE:0.5:1:24000 ",
            "RRA:AVERAGE:0.5:12:24000",
            "RRA:AVERAGE:0.5:30:24000",
            "RRA:AVERAGE:0.5:120:24000",
            "RRA:AVERAGE:0.5:1440:24000",
            "RRA:MIN:0.5:1:24000 ",
            "RRA:MIN:0.5:12:24000",
            "RRA:MIN:0.5:30:24000",
            "RRA:MIN:0.5:120:24000",
            "RRA:MIN:0.5:1440:24000",
            "RRA:MAX:0.5:1:24000 ",
            "RRA:MAX:0.5:12:24000",
            "RRA:MAX:0.5:30:24000",
            "RRA:MAX:0.5:120:24000",
            "RRA:MAX:0.5:1440:24000"]
        keys = ["DS:%s:GAUGE:120:U:U" % value[0][0:19] for value in values]
        command = [ 'create', filename, '-s', '60'] + keys + rras
        rrdtool(*command)
    update = 'N:%s' % ':'.join([str(value[1]) for value in values])

    rrdtool('update', filename, update)


def b2i(value):
    if value is True:
        return 1
    elif value is False:
        return 0
    else:
        return 'U'


def pick_object(object_list, object_type):
    otl = len(object_type)
    for obj in object_list:
        if obj['object_key'][0:otl] == object_type:
            return obj


def pick_objects(object_list, object_type):
    otl = len(object_type)
    for obj in object_list:
        if obj['object_key'][0:otl] == object_type:
            yield obj


class NestThermostat():
    def __init__(self, structure, thermostat, data, serial):
        self.name = thermostat['name']
        self.temperature = thermostat['current_temperature']
        self.fan = thermostat['hvac_fan_state']
        self.cool = thermostat['hvac_ac_state']
        self.heat = thermostat['hvac_heater_state']
        self.serial = serial
        self.structure = structure
        self.track = pick_object(data['objects'], 'track.%s' % serial)['value']
        self.shared = pick_object(data['objects'], 'shared.%s' % serial)['value']
        self.device = pick_object(data['objects'], 'device.%s' % serial)['value']

    def __repr__(self):
        return "<NestThermostat %s / Serial %s [ Temperature: %s / Heat: %s / Cool: %s / Fan: %s ]>" % (
            self.name,
            self.serial,
            self.temperature,
            self.heat,
            self.cool,
            self.fan
        )

    def to_rrd(self, base_dir):
        vars = [
            ('hvac_ac_state', b2i(self.shared['hvac_ac_state'])),
            ('hvac_heater_state', b2i(self.shared['hvac_heater_state'])),
            ('hvac_fan_state', b2i(self.shared['hvac_fan_state'])),
            ('hvac_alt_heat_x2_state', b2i(self.shared['hvac_alt_heat_x2_state'])),
            ('compressor_lockout_enabled', b2i(self.shared['compressor_lockout_enabled'])),
            ('can_heat', b2i(self.shared['can_heat'])),
            ('hvac_aux_heater_state', b2i(self.shared['hvac_aux_heater_state'])),
            ('target_change_pending', b2i(self.shared['target_change_pending'])),
            ('hvac_heat_x2_state', b2i(self.shared['hvac_heat_x2_state'])),
            ('hvac_heat_x3_state', b2i(self.shared['hvac_heat_x3_state'])),
            ('hvac_cool_x2_state', b2i(self.shared['hvac_cool_x2_state'])),
            ('hvac_emer_heat_state', b2i(self.shared['hvac_emer_heat_state'])),
            ('can_cool', b2i(self.shared['can_cool'])),
            ('hvac_alt_heat_state', b2i(self.shared['hvac_alt_heat_state'])),
            ('current_temp', self.shared['current_temperature']),
            ('target_temp_low', self.shared['target_temperature_low']),
            ('target_temp_high', self.shared['target_temperature_high'])
        ]
        rrdupdate(base_dir, "thermostat-%s" % self.serial, vars)

        vars.append(('target_temperature', self.shared['target_temperature']))
        rrdupdate(base_dir, "thermostat-c-%s" % self.serial, vars)

        if self.device['time_to_target'] > 0:
            self.device['time_to_target'] - time.time()
        else:
            time_to_target = 'U'

        device_vars = [
            ('leaf_away_low', self.device['leaf_away_low']),
            ('leaf_away_high', self.device['leaf_away_high']),
            ('leaf_threshold_heat', self.device['leaf_threshold_heat']),
            ('leaf_threshold_cool', self.device['leaf_threshold_cool']),
            ('compressor_lockout_leaf', self.device['compressor_lockout_leaf']),
            ('leaf_schedule_delta', self.device['leaf_schedule_delta']),
            ('leaf', b2i(self.device['leaf'])),

            ('fan_cooling_state', b2i(self.device['fan_cooling_state'])),
            ('fan_cooling_enabled', b2i(self.device['fan_cooling_enabled'])),
            ('target_humidity_enabled', b2i(self.device['target_humidity_enabled'])),
            ('target_humidity', self.device['target_humidity']),
            ('current_humidity', self.device['current_humidity']),
            ('target_time_confidence', self.device['target_time_confidence']),
            ('auto_dehum_enabled', b2i(self.device['auto_dehum_enabled'])),
            ('battery_level', self.device['battery_level']),
            ('time_to_target', time_to_target),
            ('away_temp_low', self.device['away_temperature_low']),
            ('away_temp_high', self.device['away_temperature_high']),
            ('away_temp_low_enabled', b2i(self.device['away_temperature_low_enabled'])),
            ('away_temp_high_enabled', b2i(self.device['away_temperature_high_enabled'])),
            ('safety_temp_activating_hvac', b2i(self.device['safety_temp_activating_hvac'])),
            ('upper_safety_temp_enabled', b2i(self.device['upper_safety_temp_enabled'])),
            ('lower_safety_temp_enabled', b2i(self.device['lower_safety_temp_enabled'])),
            ('hvac_safety_shutoff_active', b2i(self.device['hvac_safety_shutoff_active'])),
            ('upper_safety_temp', self.device['upper_safety_temp']),
            ('lower_safety_temp', self.device['lower_safety_temp']),
        ]
        rrdupdate(base_dir, "device-%s" % self.serial, device_vars)

    def set_thermostat_shared(self, **kwargs):
        equal = True

        for key in kwargs:
            if self.shared[key] != kwargs[key]:
                equal = False
                break

        if equal is True:
            raise NothingToDo()
        return self.structure.account._make_request("/v2/put/shared." + self.serial, data = kwargs)

    def set_thermostat_device(self, **kwargs):
        equal = True
        for key in kwargs:
            if self.device[key] != kwargs[key]:
                equal = False
                break

        if equal is True:
            raise NothingToDo()
        return self.structure.account._make_request("/v2/put/device." + self.serial, data = kwargs)

    def set_auto_away(self, enabled):
        # AKA Nest API:
        # {"auto_away_enable":true}
        return self.set_thermostat_device(auto_away_enable = string_to_bool(enabled))

    def set_learning(self, enabled):
        # AKA Nest API:
        # {"learning_mode":true}
        return self.set_thermostat_device(learning_mode = string_to_bool(enabled))

    def set_preconditioning(self, enabled):
        # AKA Nest UI:
        # time-to-temp
        # AKA Nest API:
        # {"preconditioning_enabled":true}
        return self.set_thermostat_device(preconditioning_enabled = string_to_bool(enabled))

    def set_radiant_control(self, enabled):
        # AKA Nest UI:
        # true radiant
        # AKA Nest API:
        # {"radiant_control_enabled":true}
        return self.set_thermostat_device(radiant_control_enabled = string_to_bool(enabled))

    def set_sunlight_correction(self, enabled):
        # AKA Nest UI:
        # sunblock
        # AKA Nest API:
        # {"sunlight_correction_enabled":false}
        return self.set_thermostat_device(sunlight_correction_enabled = string_to_bool(enabled))

    def set_fan_cooling(self, enabled):
        # AKA Nest UI:
        # airwave
        # AKA Nest API:
        # {"fan_cooling_enabled":true}
        return self.set_thermostat_device(fan_cooling_enabled = string_to_bool(enabled))

    def set_auto_dehumidify(self, enabled):
        # AKA Nest UI:
        # cool-to-dry
        # AKA Nest API:
        # {"auto_dehum_enabled":true}
        return self.set_thermostat_device(auto_dehum_enabled = string_to_bool(enabled))

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
        self.structure = structure
        for device in structure['devices']:
            serial = device[7:]
            self.thermostat_list.append(NestThermostat(self, pick_object(data['objects'], 'shared.%s' % serial)['value'], data, serial))

    def set_structure(self, **kwargs):
        equal = True
        skip = [ 'away_timestamp']
        for key in kwargs:
            if key in skip:
                continue
            if self.structure[key] != kwargs[key]:
                equal = False
                break

        if equal is True:
            raise NothingToDo()

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

    def to_rrd(self, base_dir):
        return "%d" % self.away

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
        self.user_data = self._make_request("/v5/mobile/user.%s" % self.userid)
        self.structure_list = []
        for structure in pick_objects(self.user_data['objects'], 'structure'):
            self.structure_list.append(NestStructure(self, structure['value'], self.user_data, uuid = structure['object_key']))

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
    parser.add_option("-j", "--json", dest="json", default = False)
    parser.add_option("-r", "--rrd", dest="rrd", default = False)

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

    if options.json:
        json_tmp = "%s.tmp" % options.json
        json_fh = open(json_tmp, 'w')
        json.dump(nest.user_data, json_fh, indent = 4)
        json_fh.close()
        os.rename(json_tmp, options.json)

    if options.list:
        print nest
        for structure in nest.structures():
            print "    %s" % structure
            for thermostat in structure.thermostats():
                print "        %s" % thermostat
        sys.exit(0)

    if options.rrd:
        print nest
        for structure in nest.structures():
            structure.to_rrd(options.rrd)
            print "    %s" % structure
            for thermostat in structure.thermostats():
                thermostat.to_rrd(options.rrd)
                print "        %s" % thermostat
        sys.exit(0)

    control = False

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
        'mode': ( 'set_mode', 1),
        'auto-away': ( 'set_auto_away', 1),
        'auto-schedule': ( 'set_learning', 1),
        'early-on': ( 'set_preconditioning', 1),
        'true-radiant': ( 'set_radiant_control', 1),
        'cool-to-dry': ( 'set_auto_dehumidify', 1),
        'sunblock': ( 'set_sunlight_correction', 1),
        'airwave': ('set_fan_cooling', 1),
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
    elif control == "structures":
        command_map = structure_command_map
        for structure_kwargs in structures:
            for structure in nest.structures(**structure_kwargs):
                nest_controls.append(structure)
    else:
        print "Expecting a valid combination of -s/-t/-w/-u"
        sys.exit(1)

    print "Controlling:"
    for nest_control in nest_controls:
        print "    %s" % nest_control

    args_s = list(args)
    for nest_control in nest_controls:
        args = list(args_s)
        while len(args) > 0:
            command = args.pop(0)
            try:
                function = command_map[command]
            except KeyError:
                print "%s is not a valid command for a %s" % (command, control[:-1])
                sys.exit(1)
            method = getattr(nest_control, function[0])
            function_args = []
            for i in range(0, function[1]):
                function_args.append(args.pop(0))
            try:
                sys.stdout.write("%s(%s)" % (method, function_args))
                sys.stdout.flush()
                result = method(*function_args)
                sys.stdout.write(" = %s\n" % result)
            except NothingToDo:
                sys.stdout.write(" = skipped - NothingToDo\n")
                pass
