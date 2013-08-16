import json

from pynest import NestAccount, j_dump

settings = json.load(open("pynest.json", "r"))

nest = NestAccount(settings['username'], settings['password'])

request_json = json.load(open("subscribe.request.json","r"))


sub_r = nest._make_request("/v2/subscribe", request_json)


for day in sub_r['days']:
    for event in day['events']:
        j_dump(event)
