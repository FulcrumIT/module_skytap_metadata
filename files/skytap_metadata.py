#! /bin/env python

# skytap.py
# Collect info from the skytap JSON and save it
# so facter can read it into facts for puppet
#
# Tasks:
# Get the default gateway
# Collect JSON from http://<gateway>/skytap
# Parse configuration id from "configuration_url"
# Change all keys to "skytap_XXX"
# discard hardware and interfaces blocks
# return json into file: skytap.json

import json
import sys
import os
import socket
import os.path
import yaml

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
    """Change all keys to skytap_xxx."""
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

vpn_nat_addresses = data["skytap_interfaces"][0]["skytap_nat_addresses"]["skytap_vpn_nat_addresses"]

for a in vpn_nat_addresses:
    data["skytap_nat_ip_" + a["skytap_vpn_id"]] = a["skytap_ip_address"]

# Renaming for easier readability in facter output
data["skytap_env_user_data"] = data["skytap_configuration_user_data"]
data["skytap_vm_user_data"] = data["skytap_user_data"]


def is_valid_yaml(yamlObj, type):
    """Return true if passed parameter is in valid YAML format."""
    try:
        yaml.load(yamlObj)
    except (yaml.scanner.ScannerError, AttributeError), e:
        data["skytap_" + type + "_user_data_status"] = "error"
        data["skytap_" + type + "_user_data_status"] = e
        return False
    return True


def make_user_data(type):
    """Create user data facts for vm or environment."""
    data["skytap_" + type + "_user_data_status"] = "good"
    if is_valid_yaml(data["skytap_" + type + "_user_data"], type):
        if len(data["skytap_" + type + "_user_data"]) == 0:
            data["skytap_" + type + "_user_data_status"] = "empty"
        else:
            yamlUserData = yaml.load(data["skytap_" + type + "_user_data"])
            for n in yamlUserData:
                data["skytap_" + type + "_user_data_" + n] = yamlUserData[n]


make_user_data("vm")
make_user_data("env")

del data["skytap_user_data"]
del data["skytap_configuration_user_data"]
del data["skytap_vm_user_data"]
del data["skytap_env_user_data"]
del data["skytap_interfaces"]
del data["skytap_hardware"]
del data["skytap_credentials"]
del data["skytap_local_mouse_cursor"]
del data["skytap_desktop_resizable"]

for k in data:
    print "%s=%s" % (k, data[k])

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
    if vms == vmid:
        good = True

if not good:
    history.append(vmid)

print "skytap_vm_history=" + json.dumps(history)

json.dump(history, open(vm_history_log, 'w+'))
