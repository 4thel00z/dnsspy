#! /bin/env python3
""""
Copyright 2017 Mohamed M. Tahrioui
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import asyncio
import functools
import socket
import typing
from itertools import product
from string import ascii_lowercase, digits

import aiohttp
import async_timeout

from static.subdomains import subdomains
from static.tlds import tlds

SUCCESSFUL_MAPPED_HOSTS = {}
SUBPROCESS_COUNT = 0
SUBPROCESS_MAX_COUNT = 50
WAIT_INTERVALL = 0.1
WORDLIST_URL = "https://github.com/dwyl/english-words/blob/master/words.txt?raw=true"

ENUMERATOR_QUEUE = []


class Mode:
    HOST_ENUMERATION = 0


def possible_hosts(length):
    for host in (''.join(i) for i in product(ascii_lowercase + digits + "-", repeat=length)):
        yield host


def handle_connection_error(url):
    print("{url} could not be retireved".format(url=url))
    # FIXME: add a mantainer task for deferred retries
    ENUMERATOR_QUEUE.append(url)


async def fetch(session, url, *, loop):
    with async_timeout.timeout(10, loop=loop):
        try:
            async with session.get(url) as response:
                return await response.text()
        except aiohttp.client_exceptions.ClientConnectorError:
            handle_connection_error(url)


async def wordlist(loop):
    global WORDLIST_URL
    with aiohttp.ClientSession(loop=loop) as session:
        content = await fetch(session, WORDLIST_URL, loop=loop)
        return content


def possible_domain(subdomain, host, tld):
    return ".".join([subdomain, host, tld])


async def print_current_map():
    print(SUCCESSFUL_MAPPED_HOSTS)


async def _enumerate_hosts(*, loop):
    for subdomain in subdomains:
        for tld in tlds:
            for host in await wordlist(loop):
                domain = possible_domain(subdomain=subdomain, host=host, tld=tld)
                print("processing {domain}..".format(domain=domain))
                await asyncio.ensure_future(execute(domain, loop=loop))
                print("processed {domain}...".format(domain=domain))


async def resolve(host, *, loop):
    try:
        return socket.gethostbyname(host)
    except:
        return None


async def execute(host, *, loop):
    try:

        ip = await resolve(host, loop=loop)
        await asyncio.ensure_future(print_current_map(), loop=loop)

        if ip is not None and ip.strip() != "":

            return_code, is_possible_target = await asyncio.ensure_future(can_be_taken_over(host=host, loop=loop))
            SUCCESSFUL_MAPPED_HOSTS[host] = {"ip": ip, "takeover": return_code == 0 and is_possible_target,
                                             "claimed": True}
        else:
            SUCCESSFUL_MAPPED_HOSTS[host] = {"ip": ip, "takeover": False, "claimed": False}
            # print("{payload} : {ip}".format(payload=host_name, ip=ip))
    except socket.gaierror:
        pass


class DigProtocol(asyncio.SubprocessProtocol):
    FD_NAMES = ['stdin', 'stdout', 'stderr']

    def __init__(self, done_future):
        self.done = done_future
        self.buffer = bytearray()
        super().__init__()

    def connection_made(self, transport):
        # print('process started {}'.format(transport.get_pid()))
        self.transport = transport

    def pipe_data_received(self, fd, data):
        # print('read {} bytes from {}'.format(len(data), self.FD_NAMES[fd]))
        if fd == 1:
            self.buffer.extend(data)

    def process_exited(self):
        # print('process exited')
        return_code = self.transport.get_returncode()
        # print('return code {}'.format(return_code))
        if not return_code:
            cmd_output = bytes(self.buffer).decode("utf-8")
            results = self._parse_results(cmd_output)
        else:
            results = []
        self.done.set_result((return_code, results))

    def _parse_results(self, output: typing.Optional[str]) -> bool:

        if not output or (isinstance(output, str) and output.strip() == ""):
            return False
        return "status: SERVFAIL" in output


async def can_be_taken_over(host, *, loop):
    global SUBPROCESS_COUNT, SUBPROCESS_MAX_COUNT
    while SUBPROCESS_COUNT >= SUBPROCESS_MAX_COUNT:
        await asyncio.sleep(WAIT_INTERVALL, loop=loop)

    SUBPROCESS_COUNT += 1
    cmd_done = asyncio.Future(loop=loop)
    factory = functools.partial(DigProtocol, cmd_done)
    proc = loop.subprocess_exec(
        factory,
        'dig', 'NS {host}'.format(host=host),
        stdin=None,
        stderr=None,
    )
    transport = None
    try:
        transport, protocol = await proc
        await cmd_done
    finally:
        if transport is not None:
            transport.close()

    SUBPROCESS_COUNT -= 1
    return cmd_done.result()


def run(args, mode):
    if mode == Mode.HOST_ENUMERATION:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(_enumerate_hosts(loop=loop))

# TODO:
# Replace all calls to print with logger calls (use swag)
#
#
#
