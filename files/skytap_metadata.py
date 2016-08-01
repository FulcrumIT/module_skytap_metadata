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

try:
    import requests
except ImportError:
    sys.stderr.write("You do not have the 'requests' module installed. "
                     "Please see http://docs.python-requests.org/en/latest/ "
                     "for more information.")
    exit(1)

# Collect JSON from http://<gateway>/skytap

gateway = "169.254.169.254"
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
try:
    data["skytap_metadata"] = data["skytap_configuration_user_data"].replace("-", "\"-\"")
except AttributeError:
    # There is no metadata
    data["skytap_metadata"] = data["skytap_configuration_user_data"]

try:
    data["skytap_userdata"] = data["skytap_user_data"].replace("-", "\"-\"")
except AttributeError:
    # There is no userdata
    data["skytap_userdata"] = data["skytap_user_data"]


def is_valid_yaml(yamlObj, type):
    """Return true if passed parameter is in valid YAML format."""
    try:
        yaml.load(yamlObj)
    except (yaml.scanner.ScannerError, AttributeError), e:
        data["skytap_" + type + "_status"] = "error"
        data["skytap_" + type + "_status"] = e
        return False
    return True


def make_data(type):
    """Create data facts for vm/env."""
    data["skytap_" + type + "_status"] = "good"
    if is_valid_yaml(data["skytap_" + type], type):
        if len(data["skytap_" + type]) == 0:
            data["skytap_" + type + "_status"] = "empty"
        else:
            yamlUserData = yaml.load(data["skytap_" + type])
            for n in yamlUserData:
                data["skytap_" + type + "_" + n] = yamlUserData[n]


make_data("metadata")
make_data("userdata")

del data["skytap_user_data"]
del data["skytap_configuration_user_data"]
del data["skytap_userdata"]
del data["skytap_metadata"]
del data["skytap_interfaces"]
del data["skytap_hardware"]
del data["skytap_credentials"]
del data["skytap_local_mouse_cursor"]
del data["skytap_desktop_resizable"]

for k in data:
    try:
        data[k].strip()
        print "%s=%s" % (k.strip(), data[k].strip())
    except AttributeError:
        print "%s=%s" % (k.strip(), data[k])

# Parse stuff from local_roles.txt

f = open("local_roles.txt", "r")

lines = f.readlines()
new_lines = []

for line in lines:
    if "=" in line:
        key = line.split("=")[0].replace("#", "").strip()
        value = line.split("=")[1].strip()
        print key + "=" + value

        if line.strip()[0] != "#":
            new_lines.append("# " + line.strip())
        else:
            new_lines.append(line.strip())

f.close()

f = open("local_roles.txt", "w+")

for line in new_lines:
    f.write(line + "\n")

f.close()
