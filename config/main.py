#!/usr/sbin/env python

import sys
import os
import click
import json
import subprocess
from swsssdk import ConfigDBConnector

SONIC_CFGGEN_PATH = '/usr/local/bin/sonic-cfggen'
MINIGRAPH_PATH = '/etc/sonic/minigraph.xml'
MINIGRAPH_BGP_SESSIONS = 'minigraph_bgp'

#
# Helper functions
#

# Get BGP neighbor list from minigraph
def _get_neighbor_list():
    proc = subprocess.Popen([SONIC_CFGGEN_PATH, '-m', MINIGRAPH_PATH, '--var-json', MINIGRAPH_BGP_SESSIONS],
                            stdout=subprocess.PIPE,
                            shell=False,
                            stderr=subprocess.STDOUT)
    stdout = proc.communicate()[0]
    proc.wait()
    return json.loads(stdout.rstrip('\n'))
 
# Returns True if a neighbor has the IP address <ipaddress>, False if not
def _is_neighbor_ipaddress(ipaddress):
    bgp_session_list = _get_neighbor_list()
    for session in bgp_session_list:
        if session['addr'] == ipaddress:
            return True
    return False

# Returns string containing IP address of neighbor with hostname <hostname> or None if <hostname> not a neighbor
def _get_neighbor_ipaddress_by_hostname(hostname):
    bgp_session_list = _get_neighbor_list()
    for session in bgp_session_list:
        if session['name'] == hostname:
            return session['addr'];
    return None

# Start up or shut down all BGP session
def _switch_bgp_admin_status_all(state):
    bgp_session_list = _get_neighbor_list()
    config_db = ConfigDBConnector()
    config_db.connect()
    for session in bgp_session_list:
        ipaddress = session['addr']
        config_db.set_entry('bgp_neighbor', ipaddress, {'admin_status': state})

# Start up or shut down BGP session by neighbor IP address or hostname
def _switch_bgp_admin_status(ipaddr_or_hostname, state):
    if _is_neighbor_ipaddress(ipaddr_or_hostname):
        ipaddress = ipaddr_or_hostname
    else:
        # If <ipaddr_or_hostname> is not the IP address of a neighbor, check to see if it's a hostname
        ipaddress = _get_neighbor_ipaddress_by_hostname(ipaddr_or_hostname)

    if ipaddress == None:
        print "Error: could not locate neighbor '{}'".format(ipaddr_or_hostname)
        raise click.Abort

    config_db = ConfigDBConnector()
    config_db.connect()
    config_db.set_entry('bgp_neighbor', ipaddress, {'admin_status': state})

# Run bash command and print output to stdout
def run_command(command, pager=False):
    click.echo(click.style("Command: ", fg='cyan') + click.style(command, fg='green'))
    p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    if pager is True:
        click.echo_via_pager(p.stdout.read())
    else:
        click.echo(p.stdout.read())
    p.wait()
    if p.returncode != 0:
        sys.exit(p.returncode)


# This is our main entrypoint - the main 'config' command
@click.group()
def cli():
    """SONiC command line - 'config' command"""
    if os.geteuid() != 0:
        exit("Root privileges are required for this operation")

#
# 'bgp' group
#

@cli.group()
def bgp():
    """BGP-related tasks"""
    pass

#
# 'shutdown' subgroup
#

@bgp.group()
def shutdown():
    """Shut down BGP session(s)"""
    pass


# 'neighbor' subcommand
@shutdown.command()
@click.argument('ipaddr_or_hostname', required=True)
def neighbor(ipaddr_or_hostname):
    """Shut down BGP session by neighbor IP address or hostname"""
    _switch_bgp_admin_status(ipaddr_or_hostname, 'down')

@shutdown.command()
def all():
    _switch_bgp_admin_status_all('down')

@bgp.group()
def startup():
    """Start up BGP session(s)"""
    pass


# 'neighbor' subcommand
@startup.command()
@click.argument('ipaddr_or_hostname', required=True)
def neighbor(ipaddr_or_hostname):
    """Start up BGP session by neighbor IP address or hostname"""
    _switch_bgp_admin_status(ipaddr_or_hostname, 'up')

@startup.command()
def all():
    _switch_bgp_admin_status_all('up')


if __name__ == '__main__':
    cli()

