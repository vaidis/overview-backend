#! /usr/bin/env python3.6

import os
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

# import webserver
import check

servers = "servers.csv"
data = []
host_details = {}


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

    if len(data) == 0:
        for row in reader:
            data.append(dict(row))


async def get_host_details(address, port, command):
    await asyncio.sleep(0.05)
    global data
    cmd = "ssh -o ConnectTimeout=4  root@" + address + " -p " + port + " '" + command + "'"
    result = subprocess.check_output(cmd, shell=True).decode("utf-8")
    return str(result)


async def get_check_values(lopp):
    global data
    while True:
        await asyncio.sleep(1)
        for host in data:
            for key, value in list(host.items()):
                if key == 'address':
                    address = str(host[key])
                    try:
                        if host['ping'] == "True":
                            port = host['port']
                            host['root_usage'] = str(await check.root_usage(address, port))
                            taglist = host['tags'].split(",")

                            # TODO: check ssh connectivity before use it
                            for tag in taglist:
                                if tag == "checkgeo":
                                    host['checkgeo'] = await check.geo(address)
                                if tag == "checktemp":
                                    host['checktemp'] = await check.temp(address, port)
                                if tag == "checkraid":
                                    host['checkraid'] = await check.raid(address, port)

                        else:
                            #print("get_check_values() root_usage : " + address +  " : PING FALSE")
                            if host.get('root_usage'): del host['root_usage']
                            if host.get('checkgeo'): del host['checkgeo']
                            if host.get('checkraid'): del host['checkraid']
                            if host.get('checktemp'): del host['checktemp']
                    except:
                        pass


async def check_ping(lopp, data):
    while True:
        for host in data:
            for key, value in list(host.items()):
                if key == 'address':
                    address = str(host[key])

                    try:
                        await asyncio.sleep(0.05)
                        host['ping'], host['latency'] = await check.network(address)
                    except:
                        host['ping'] = 'False'


async def main(lopp):
    global data
    addresses = []
    init_data()
    await asyncio.gather(
       check_ping(loop, data),
       get_check_values(loop),
    )


async def dashboard(request):
    text = json.dumps([data])
    return web.Response(text=text)


async def host_details(request):
    global host_details
    global data
    #print("host: " + str(request))
    host_address = "{}".format(request.rel_url.query['address'])
    command = "{}".format(request.rel_url.query['command'])

    for host in data:
        for key, value in list(host.items()):
            if key == 'address':
                address = str(host[key])
                if address == host_address:
                    port = host['port']


    if command == "dmesg":
        result = await get_host_details(host_address, port, "dmesg | tail -n 200")
    if command == "ps":
        result = await get_host_details(host_address, port, "ps aufx")
    if command == "free":
        result = await get_host_details(host_address, port, "free -m")
    if command == "mount":
        result = await get_host_details(host_address, port, "mount")
    if command == "df":
        result = await get_host_details(host_address, port, "df -h")
    if command == "netstat":
        result = await get_host_details(host_address, port, "netstat -tulpn")
    if command == "route":
        result = await get_host_details(host_address, port, "route -n")
    if command == "ifconfig":
        result = await get_host_details(host_address, port, "ifconfig -a")
    if command == "time":
        result = await get_host_details(host_address, port, "date")

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
