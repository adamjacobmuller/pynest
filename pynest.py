import urllib2
import urllib
import json
import pprint
import time


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
        data['track'][serial]

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
        return self.set_thermostat_shared(target_change_pending = True, target_temperature = temperature)

    def set_mode(self, mode):
        # heat|cool|range|off
        return self.set_thermostat_shared(target_temperature_type = mode)

    def set_fan_timer_timeout(self, timeout):
        # epoch seconds, when to turn off fan
        return self.set_thermostat_device(fan_timer_timeout = timeout)

    def set_fan_timer_duration(self, duration):
        # seconds
        return self.set_thermostat_device(fan_timer_duration = duration)

    def set_fan_duty_cycle(self, duty_cycle):
        # seconds per hour
        return self.set_thermostat_device(fan_duty_cycle = duty_cycle)

    def set_fan_duty_range(self, start, end):
        # seconds
        return self.set_thermostat_device(fan_duty_start_time = start, fan_duty_end_time = end)

    def set_fan_mode(self, mode):
        # on|off|auto|duty-cycle
        return self.set_thermostat_device(fan_mode = mode)


class NestStructure():
    def __init__(self, account, structure, data, uuid):
        self.account = account
        self.name = structure['name']
        self.away = structure['away']
        self.uuid = uuid
        self.thermostats = []
        for device in structure['devices']:
            serial = device[7:]
            self.thermostats.append(NestThermostat(self, data['shared'][serial], data, serial))

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

    def thermostat(self, **kwargs):
        for thermostat in self.thermostats:
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

    def structure(self, **kwargs):
        for structure in self.structures:
            match = True
            for arg in kwargs:
                if getattr(structure, arg) != kwargs[arg]:
                    match = False
                    break
            if match is True:
                return structure

    def load(self):
        req = self._make_request("/v2/mobile/user.%s" % self.userid)
        self.structures = []
        for structure in req['structure']:
            self.structures.append(NestStructure(self, req['structure'][structure], req, uuid = structure))

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


if __name__ == "__main__":
    if False:
        handler = urllib2.HTTPSHandler(debuglevel=1)
        handler.set_http_debuglevel(1)
        opener = urllib2.build_opener(handler)
        urllib2.install_opener(opener)

    settings = json.load(open("pynest.json", "r"))

    nest = NestAccount(settings['username'], settings['password'])
    for structure in ['Home']:
        for thermostat in ['Upstairs', 'Downstairs']:
            nest.structure(name=structure).thermostat(name=thermostat).set_fan_duty_cycle(900)
            nest.structure(name=structure).thermostat(name=thermostat).set_fan_duty_range(60 * 60 * 8, 60 * 60 * 23)
            nest.structure(name=structure).thermostat(name=thermostat).set_fan_mode("duty-cycle")
    #print nest.structure(name="Home").thermostat(name="Upstairs").set_fan_duty_cycle(900)
    #print nest.structure(name="Home").thermostat(name="Downstairs").set_fan("on")
    #print nest.structure(name="Home").thermostat(name="Downstairs").set_temperature(27)
    #print nest.structure(name="Home").thermostat(name="Basement").set_temperature(10)
    print nest
    for structure in nest.structures:
        print "    %s" % structure
        for thermostat in structure.thermostats:
            print "        %s" % thermostat
        #    thermostat.set_temperature(27)
        #structure.set_back()
