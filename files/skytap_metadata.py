#! /bin/env python

# skytap.py
# Collect info from the skytap JSON and save it
# so facter can read it into facts for puppet
#
# Tasks:
#   Get the default gateway
#   Collect JSON from http://<gateway>/skytap
#   Parse configuration id from "configuration_url"
#	Change all keys to "skytap_XXX"
#	discard hardware and interfaces blocks
#	return json into file: skytap.json

import json
import sys
import os
import socket
import shutil
import os.path

vm_history_log = "/var/log/skytap-history.log"

try:
    import requests
except ImportError:
    sys.stderr.write("You do not have the 'requests' module installed. "
        "Please see http://docs.python-requests.org/en/latest/ "
        "for more information.")
    exit(1)

# Get the default gateway

file = os.popen("/sbin/ip route | awk '/default/ {print $3}'")
gateway = file.read().strip()
file.close()

# Quick test to see if the gateway actually looks like an IP address
try:
    socket.inet_aton(gateway)
except socket.error:
    sys.stderr.write("Could not determine the gateway.")
    exit(1)

# Collect JSON from http://<gateway>/skytap

url = 'http://' + gateway + '/skytap'

json_data = requests.get(url)

if json_data.status_code != 200:
    sys.stderr.write("Error received by JSON request. "
        "Status code: " + json_data.status_code)
    exit(1)

if json_data.headers['content-type'] != 'application/json':
    sys.stderr.write("Returned text from server isn't a JSON. "
        "Content-type: " + json_data.headers['content-type'])
    exit(1)


def add_skytap(obj):
    for key in obj.keys():
        if key[:7] != "skytap_":
            new_key = "skytap_" + key
            obj[new_key] = obj[key]
            del obj[key]
    return obj

data = json.loads(json_data.text, object_hook=add_skytap)

configid = data["skytap_configuration_url"].split("/")[-1]
data["skytap_envid"] = configid

data["skytap_vmid"] = data["skytap_id"]
del data["skytap_id"]

data["skytap_hardware_uuid"] = data["skytap_hardware"]["skytap_uuid"]

del data["skytap_interfaces"]
del data["skytap_hardware"]
del data["skytap_credentials"]
del data["skytap_local_mouse_cursor"]
del data["skytap_desktop_resizable"]

metapath = '/etc/puppetlabs/facter/facts.d/skytap.json'
metafile = open(metapath, 'w+')
json.dump(data, metafile)

# Add a history of machine ids to a file. This number will change if
# the machine ID changes - that is, if the machine was copied as a
# template or similar.

vmid = data["skytap_vmid"]

if os.path.exists(vm_history_log):
    with open(vm_history_log) as data_file:    
        history = json.load(data_file)
else:
    history = []

good = False

for vms in history:
    print vms
    if vms == vmid:
        good = True

if not good:
    history.append(vmid)

print history
