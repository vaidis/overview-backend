import re
import time
import asyncio
import subprocess
import asyncio.subprocess
from async_timeout import timeout
from bs4 import BeautifulSoup


async def upsstatus(address):
    await asyncio.sleep(0.05)
    result = "0"
    cmd = "/opt/upsmon/upsstatus.sh " + address
    process = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE)
    stdout, stderr = await process.communicate()
    result = stdout.decode("utf-8").strip()
    return result


async def upscapacity(address):
    await asyncio.sleep(0.05)
    result = "0"
    cmd = "/opt/upsmon/upscapacity.sh " + address
    process = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE)
    stdout, stderr = await process.communicate()
    result = stdout.decode("utf-8").strip()
    return result


async def geo(address):
    await asyncio.sleep(0.05)
    result = "0"
    cmd = "curl -m 8 --connect-timeout 8 -Is http://" + address + ":8080/geoserver | head -1 | awk {'print $2}'"
    process = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE)
    stdout, stderr = await process.communicate()
    result = stdout.decode("utf-8").strip()

    if (result == "302"):
        return "True"
    else:
        return "False"

async def clock(address, port):
    print("clock " + str(address) + ":" + str(port))
    cmd = "ssh root@" + address + " -p " + port + " date +'%s'"
    process = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE)
    stdout, stderr = await process.communicate()
    result = stdout.decode("utf-8").strip()

    difference = remoteclock - localclock
    print("clock difference: " + str(difference))

    return difference

    if (result == "302"):
        return "True"
    else:
        return "False"


async def raid(address, port):
    await asyncio.sleep(0.05)
    global data
    cmd = "ssh root@" + address + " -p " + port + " 'megaraid_status.py' | grep -e 'HDD\|SSD' | awk -F\| '{print $5}'"
    process = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE)
    stdout, stderr = await process.communicate()
    result = stdout.decode("utf-8").strip()

    disks = result.split("\n")
    for disk in disks:
        if disk.strip() != "Online, Spun Up":
            return "False"
        else:
            return "True"


async def temp(address, port):
    await asyncio.sleep(0.05)
    cmd = "ssh root@" + address + " -p " + port + " cat /sys/class/thermal/thermal_zone0/temp | head -c 2"
    process = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE)

    try:
        stdout, stderr = await process.communicate()
        return stdout.decode("utf-8").strip()

    except:
        raise Exception(some_identifier_here + ' ' + traceback.format_exc())


async def disk(address, port):
    await asyncio.sleep(0.05)
    global data
    cmd = "ssh -o ConnectTimeout=4  root@" + address + " -p " + port + " 'df -Ph /' | awk 'NR == 2{print $5+0 }'"

    try:
        process = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE)
        stdout, stderr = await process.communicate()
        result = stdout.decode("utf-8").strip()
        return str(result)

    except Exception as e:
        pass

