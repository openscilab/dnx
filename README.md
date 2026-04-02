<div align="center">
    <h1>DNX: Minimal cross-platform DNS changer</h1>
    <a href="https://codecov.io/gh/openscilab/dnx"><img src="https://codecov.io/gh/openscilab/dnx/branch/main/graph/badge.svg" alt="Codecov"/></a>
    <a href="https://badge.fury.io/py/dnx"><img src="https://badge.fury.io/py/dnx.svg" alt="PyPI version"></a>
    <a href="https://www.python.org/"><img src="https://img.shields.io/badge/built%20with-Python3-green.svg" alt="built with Python3"></a>
    <a href="https://github.com/openscilab/dnx"><img alt="GitHub repo size" src="https://img.shields.io/github/repo-size/openscilab/dnx"></a>
    <a href="https://discord.gg/TODO"><img src="https://img.shields.io/discord/1064533716615049236.svg" alt="Discord Channel"></a>
</div>


## Overview

<p align="justify">
<strong>DNX</strong> is a small Python CLI and library for viewing and changing per-interface DNS servers on <strong>Linux</strong>, <strong>macOS</strong>, and <strong>Windows</strong>. It picks a sensible backend automatically (e.g. systemd-resolved, NetworkManager, or <code>/etc/resolv.conf</code> on Linux; PowerShell DNS cmdlets on Windows; <code>networksetup</code> on macOS), validates IP addresses, and can <strong>ping</strong> resolvers to show latency before or after you switch. Operations that change system DNS typically require administrator privileges.
</p>

<table>
    <tr>
        <td align="center">PyPI Counter</td>
        <td align="center">
            <a href="https://pepy.tech/projects/dnx">
                <img src="https://static.pepy.tech/badge/dnx" alt="PyPI downloads">
            </a>
        </td>
    </tr>
    <tr>
        <td align="center">Github Stars</td>
        <td align="center">
            <a href="https://github.com/openscilab/dnx">
                <img src="https://img.shields.io/github/stars/openscilab/dnx.svg?style=social&label=Stars" alt="GitHub stars">
            </a>
        </td>
    </tr>
</table>

<table>
    <tr>
        <td align="center">Branch</td>
        <td align="center">main</td>
        <td align="center">dev</td>
    </tr>
    <tr>
        <td align="center">CI</td>
        <td align="center">
            <img src="https://github.com/openscilab/dnx/actions/workflows/test.yml/badge.svg?branch=main" alt="CI main">
        </td>
        <td align="center">
            <img src="https://github.com/openscilab/dnx/actions/workflows/test.yml/badge.svg?branch=dev" alt="CI dev">
        </td>
    </tr>
</table>

<table>
	<tr> 
		<td align="center">Code Quality</td>
		<td align="center"><a href="https://app.codacy.com/gh/openscilab/dnx/dashboard?utm_source=gh"><img src="https://app.codacy.com/project/badge/Grade/cb2ab6584eb443b8a33da4d4252480bc"/></a></td>
		<td align="center"><a href="https://www.codefactor.io/repository/github/openscilab/dnx"><img src="https://www.codefactor.io/repository/github/openscilab/dnx/badge" alt="CodeFactor"></a></td>
	</tr>
</table>

## Installation

### Source Code

- Download [Version 0.1](https://github.com/openscilab/dnx/archive/v0.1.zip) or [Latest Source](https://github.com/openscilab/dnx/archive/dev.zip)
- `pip install .`

### PyPI

- Check [Python Packaging User Guide](https://packaging.python.org/installing/)
- `pip install dnx==0.1`

## Usage

### Library

#### Backend and current DNS

```pycon
>>> from dnx.dns import get_backend, get_platform, Platform
>>> get_platform()
<Platform.LINUX: 'linux'>
>>> backend = get_backend()
>>> backend.get_dns()
['192.168.1.1']
```

#### Set DNS (requires admin / elevated process)

```pycon
>>> from dnx.dns import get_backend
>>> backend = get_backend()
>>> backend.set_dns(["8.8.8.8", "8.8.4.4"])
>>> backend.get_dns()
['8.8.8.8', '8.8.4.4']
```

#### Ping helpers

```pycon
>>> from dnx.ping import ping_server, verify_servers
>>> ping_server("1.1.1.1", count=2)
PingResult(ip='1.1.1.1', reachable=True, ...)
>>> verify_servers(["8.8.8.8", "1.1.1.1"])
(True, [PingResult(...), PingResult(...)])
```

#### Exceptions

```pycon
>>> from dnx.exceptions import DNXError, InvalidIPError
>>> from dnx.dns import validate_ips
>>> validate_ips(["999.0.0.1"])
Traceback (most recent call last):
...
InvalidIPError: ...
```

### CLI

ℹ️ You can use `dnx` or `python -m dnx` to run this program.

#### Version

```console
> dnx --version
dnx 0.1
```

#### List presets

```console
> dnx list
google: 8.8.8.8, 8.8.4.4
cloudflare: 1.1.1.1, 1.0.0.1
...
```

#### List presets with latency

ℹ️ Sends a few ICMP probes per preset IP (may require permission for raw ping on some systems).

```console
> dnx list --latency
Checking latency for all presets...

google:
  8.8.8.8: 12.3ms avg (0% loss)
  ...
```

#### Current DNS

```console
> dnx current
Current DNS servers:
  192.168.1.1
```

#### Current DNS with latency

```console
> dnx current --latency
Current DNS servers:
  1.1.1.1

Latency:
  1.1.1.1: 8.1ms avg (0% loss)
```

#### Set DNS (preset or IPs)

ℹ️ `set` and `reset` require an elevated shell (e.g. Administrator on Windows, `sudo` on Linux/macOS).

```console
> dnx set cloudflare
Using preset 'cloudflare': 1.1.1.1, 1.0.0.1
DNS updated successfully!

Latency comparison:
  Before:
    192.168.1.1: 2.1ms avg (0% loss)
  After:
    1.1.1.1: 9.0ms avg (0% loss)
```

```console
> dnx set 9.9.9.9 149.112.112.112 --verify
```

ℹ️ `--verify` pings first and asks before continuing if a server is unreachable. `--no-latency` skips the before/after latency block.

#### Ping only

ℹ️ Preset name or one or more IP addresses. Use `-c` / `--count` for probe count.

```console
> dnx ping cloudflare -c 4
Pinging 2 server(s)...

1.1.1.1: 7.5ms avg (0% loss)
1.0.0.1: 8.2ms avg (0% loss)
```

#### Reset to system default

```console
> dnx reset
DNS reset to system default
```

#### Interface override

ℹ️ When auto-detected interface is wrong (VPN, multiple NICs), pass `--iface` before the subcommand:

```console
> dnx --iface "Wi-Fi" current
```

## Issues & Bug Reports

Just fill an issue and describe it. We'll check it ASAP! You can also email [dnx@openscilab.com](mailto:dnx@openscilab.com).

- Please complete the issue template

You can also join our discord server

<a href="https://discord.gg/TODO">
  <img src="https://img.shields.io/discord/1064533716615049236.svg?style=for-the-badge" alt="Discord Channel">
</a>

## Show Your Support

### Star This Repo

Give a ⭐️ if this project helped you!

### Donate to our project
If you do like our project and we hope that you do, can you please support us? Our project is not and is never going to be working for profit. We need the money just so we can continue doing what we do ;-) .			

<a href="https://openscilab.com/#donation" target="_blank"><img src="https://github.com/openscilab/dnx/raw/main/otherfiles/donation.png" height="90px" width="270px" alt="ONX Donation"></a>
