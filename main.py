#! /usr/bin/env python3.6

import os
import re
import sys
import csv
import json
import time
import asyncio
import datetime
import subprocess
import aiohttp_cors
import asyncio.subprocess
from async_timeout import timeout
from aiohttp import web
from random import randint

# import webserver
import check

servers = "servers.csv"
data = {}
hosts = []
host_details = {}

# modal command keys requests
async def get_host_details(address, port, command):
    await asyncio.sleep(0.05)
    global data
    cmd = "ssh -o ConnectTimeout=4  root@" + address + " -p " + port + " '" + command + "'"
    result = subprocess.check_output(cmd, shell=True).decode("utf-8")
    return str(result)

# get values from ssh for every host based on check tags
async def get_check_values(lopp):
    global data
    while True:
        await asyncio.sleep(1)
        for host in data['hosts']:
            for key, value in list(host.items()):
                if key == 'address':
                    address = str(host[key])
                    data['current_check'] = str(address)
                    try:
                        if host['ping'] == "True":
                            port = host['port']
                            taglist = host['tags'].split(",")

                            # TODO: check ssh connectivity before using it
                            for tag in taglist:
                                if tag == "checkdisk":
                                    #host['root_usage'] = str(await check.disk(address, port))
                                    host['root_usage'] = await check.disk(address, port)
                                if tag == "checkgeo":
                                    host['checkgeo'] = await check.geo(address)
                                if tag == "checktemp":
                                    host['checktemp'] = await check.temp(address, port)
                                if tag == "checkraid":
                                    host['checkraid'] = await check.raid(address, port)
                                if tag == "checkupsstatus":
                                    host['checkupsstatus'] = await check.upsstatus(address)
                                if tag == "checkupscapacity":
                                    host['checkupscapacity'] = await check.upscapacity(address)                                    

                        else:
                            #print("get_check_values() root_usage : " + address +  " : PING FALSE")
                            if host.get('root_usage'): del host['root_usage']
                            if host.get('checkgeo'): del host['checkgeo']
                            if host.get('checkraid'): del host['checkraid']
                            if host.get('checktemp'): del host['checktemp']
                            if host.get('checkupsstatus'): del host['checkupsstatus']
                            if host.get('checkupscapacity'): del host['checkupscapacity']
                    except:
                        pass

# keep pinging that host every random seconds
async def ping(address, host):
    global data
    while True:
        await asyncio.sleep(randint(2,8))
        cmd = "/bin/ping -c 1 -w5 -W5 " + str(address)
        proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, shell=True)
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            for line in str(stdout).split(" "):
                if re.search("time=", line):
                    latency = line.replace("time=",  "")

            # print("ping " + str(address) + " \t [ OK ] " + str(latency))
            host['ping'] = "True"
            host['latency'] = str(latency)

        else:
            # print("ping " + str(address) + " \t [FAIL] ")
            host['ping'] = 'False'


# run a ping function for every host
async def check_ping(lopp, data):
    for host in data['hosts']:
        for key, value in list(host.items()):
            if key == 'address':
                address = str(host[key])
                asyncio.ensure_future(ping(address, host), loop=loop)

# convert the text file to cvs and import into the reader dict
def init_data():
    serverfile = "/root/servers"
    csvfile = serverfile + ".csv"
    cmd = "cat " + serverfile + " | sed 's/  */ /g' > " + csvfile
    subprocess.call(cmd, shell=True)
    f = open(csvfile, 'rU')
    reader = csv.DictReader(f, delimiter=' ', fieldnames=(
        "address",
        "port",
        "os_name",
        "os_ver",
        "type",
        "hostname",
        "tags"
        ))
    # fill the hosts list
    if len(hosts) == 0:
        for row in reader:
            hosts.append(dict(row))
            data['hosts'] = hosts

# MAIN
async def main(lopp):
    global data
    global hosts
    addresses = []
    init_data()
    await asyncio.gather(
       check_ping(loop, data),
       get_check_values(loop),
    )

# frontpage requests
async def dashboard(request):
    text = json.dumps([data])
    return web.Response(text=text)

# modal requests
async def host_details(request):
    global host_details
    global data
    global hosts
    print("host: " + str(request))
    host_address = "{}".format(request.rel_url.query['address'])
    command = "{}".format(request.rel_url.query['command'])

    for host in data['hosts']:
        for key, value in list(host.items()):
            if key == 'address':
                address = str(host[key])
                if address == host_address:
                    port = host['port']

    # modal command keys
    if command == "dmidecode":
        result = await get_host_details(host_address, port, "dmidecode")
    if command == "dmesg":
        result = await get_host_details(host_address, port, "dmesg | tail -n 200")
    if command == "ps":
        result = await get_host_details(host_address, port, "ps aufx")
    if command == "free":
        result = await get_host_details(host_address, port, "free -m")
    if command == "mount":
        result = await get_host_details(host_address, port, "mount")
    if command == "partitions":
        result = await get_host_details(host_address, port, "cat /proc/partitions")
    if command == "cpuinfo":
        result = await get_host_details(host_address, port, "cat /proc/cpuinfo")
    if command == "df":
        result = await get_host_details(host_address, port, "df -h")
    if command == "netstata":
        result = await get_host_details(host_address, port, "netstat -an")
    if command == "netstatt":
        result = await get_host_details(host_address, port, "netstat -tulpn")
    if command == "route":
        result = await get_host_details(host_address, port, "route -n")
    if command == "ifconfig":
        result = await get_host_details(host_address, port, "ifconfig -a")
    if command == "time":
        result = await get_host_details(host_address, port, "date")
    if command == "hwclock":
        result = await get_host_details(host_address, port, "hwclock --debug")

    text = str(result)
    return web.Response(text=text)


loop = asyncio.get_event_loop()
app = web.Application()
cors = aiohttp_cors.setup(app)

resources = [
    ['GET', r'/', dashboard],
    ['GET', r'/host', host_details]]

def add_routes(app, resources):
    routes = []
    for route in resources:
        try:
            name = route.pop(3)
        except IndexError:
            name = None
        routes.append(app.router.add_route(*route[0:3], name=name))
    return routes


routes = add_routes(app, resources)
cors = aiohttp_cors.setup(app, defaults={
    '*': aiohttp_cors.ResourceOptions(
        allow_credentials=True,
        expose_headers=("X-Custom-Server-Header", "Content-Type:application/json"),
        allow_headers=("X-Requested-With", "Content-Type"),
        max_age=3600,
    )
})

for route in routes:
    cors.add(route)

try:
    asyncio.ensure_future(main(loop))
    asyncio.ensure_future(web.run_app(app, host="0.0.0.0", port=7777))
    loop.run_forever()

except KeyboardInterrupt:
    loop.stop()
    loop.close()

finally:
    print("Closing Loop")
    loop.stop()
    loop.close()
