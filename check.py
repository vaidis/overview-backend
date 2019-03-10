import re
import asyncio
import subprocess
import asyncio.subprocess
from async_timeout import timeout


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


async def root_usage(address, port):
    await asyncio.sleep(0.05)
    global data
    cmd = "ssh -o ConnectTimeout=4  root@" + address + " -p " + port + " 'df -Ph /' | awk 'NR == 2{print $5+0 }'"
    result = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
    return str(result)


async def network(address):
    await asyncio.sleep(0.1)
    global data

    # TODO: create an async task for every host
    for waittime in [1, 2, 3]:
        cmd = "/bin/ping -c 1 -w " + str(waittime) + " -W " + str(waittime) + " " + str(address)
        proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, shell=True)
        stdout, stderr = await proc.communicate()

        if proc.returncode == 0:
            for line in str(stdout).split(" "):
                if re.search("time=", line):
                    latency = line.replace("time=",  "")

            # print("ping " + str(address) + " \t [ OK ] " + str(latency))
            return "True", str(latency)

        else:
            # print("ping " + str(address) + " \t [FAIL] " + str(waittime))
            pass

    return "False"
