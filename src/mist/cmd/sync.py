import os
import sys
import getpass

from yaml import load
from yaml.scanner import ScannerError

from mist.client import MistClient
from mist.client.helpers import machine_from_id, backend_from_id


def load_dbyaml(path):
    if not os.path.isfile(path):
        print "You need to provide a valid path for a db.yaml file"
        sys.exit(1)

    with open(path, 'r') as db_yaml:
        try:
            print ">>>Loading %s" %path
            print
            user_dict = load(db_yaml) or {}
            return user_dict
        except ScannerError:
            print "Error parsing %s" % path
            print "Maybe not a yaml file"
            sys.exit(1)


def init_client():
    print ">>>Log in to mist.io"
    email = raw_input("Email: ")
    password = getpass.getpass("Password: ")
    print
    try:
        client = MistClient(email=email, password=password)
        client.backends
        return client
    except Exception as e:
        print e
        sys.exit(1)


def add_backend(client, backend):
    title = backend.get('title')
    provider = backend.get('provider')
    key = backend.get('apikey', "")
    secret = backend.get('apisecret', "")
    tenant_name = backend.get('tenant_name', "")
    region = backend.get('region', "")
    apiurl = backend.get('apiurl', "")
    compute_endpoint = backend.get('compute_endpoint', None)
    machine_ip = backend.get('machine_ip', None)
    machine_key = backend.get('machine_key', None)
    machine_user = backend.get('machine_user', None)
    machine_port = backend.get('machine_port', None)
    client.add_backend(title, provider, key, secret, tenant_name=tenant_name, region=region, apiurl=apiurl,
                       machine_ip=machine_ip, machine_key=machine_key, machine_user=machine_user,
                       compute_endpoint=compute_endpoint, machine_port=machine_port)


def sync_backends(user_dict, client):
    added_backends = user_dict['backends']
    backends = client.backends

    print ">>>Syncing backends"
    for key in added_backends:
        if added_backends[key]['title'] in backends.keys():
            print "Found %s" % added_backends[key]['title']
        else:
            print "Adding backend %s" % added_backends[key]['title']
            add_backend(client, added_backends[key])
    print


def add_key(client, key, key_id):
    key_name = key_id
    private = key['private']
    client.add_key(key_name=key_name, private=private)

    if key['default']:
        client.update_keys()
        chosen_key = client.keys[key_id]
        chosen_key.set_default()


def sync_keys(user_dict, client):
    added_keys = user_dict['keypairs']
    keys = client.keys

    print ">>>Syncing keys"
    for key in added_keys:
        if key in keys.keys():
            print "Found %s" % key
        else:
            print "Adding key %s" % key
            add_key(client, key=added_keys[key], key_id=key)
    print


def associate_keys(user_dict, client):
    """
    This whole function is black magic, had to however cause of the way we keep key-machine association
    """
    added_keys = user_dict['keypairs']

    print ">>>Updating Keys-Machines association"
    for key in added_keys:
        machines = added_keys[key]['machines']
        if machines:
            try:
                for machine in machines:
                    backend_id = machine[0]
                    machine_id = machine[1]
                    ssh_user = machine[3]
                    ssh_port = machine[-1]
                    key = client.keys[key]
                    backend = backend_from_id(client, backend_id)
                    backend.update_machines()
                    mach = machine_from_id(backend, machine_id)
                    public_ips = mach.info.get('public_ips', None)
                    if public_ips:
                        host = public_ips[0]
                    else:
                        host = ""
                    key.associate_to_machine(backend_id=backend_id, machine_id=machine_id, host=host, ssh_port=ssh_port,
                                             ssh_user=ssh_user)

                    print "associated machine %s" % machine_id
            except Exception as e:
                pass
    client.update_keys()
    print


def sync(path):

    user_dict = load_dbyaml(path)
    client = init_client()
    sync_keys(user_dict, client)
    sync_backends(user_dict, client)
    associate_keys(user_dict, client)