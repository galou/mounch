#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: Chmouel Boudjnah <chmouel@chmouel.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# Rofi menu to jump to my preferred app, config is stored in
# ~/.config/mounch/mounch.yaml that look like this :
#
# emacs:
#   description: "Emacs"
#   binary: emacs
#   icon: emacs27
# suspend:
#   args: suspend
#   binary: systemctl
#   description: "Suspend"
#   icon: system-suspend-hibernate
# ssh:
#   args: ["-show", "ssh", "-theme",  "mounch"]
#   binary: rofi
#   description: "SSH"
#   icon: ssh
# calculate:
#   args: ["-modi", "calc:qalc +u8",
#           "-show", "calc", "-theme", "mounch", "-theme-str", '* { width: 640; height: 400;}']
#   binary: rofi
#   description: "Calculate"
#   icon: calc
#
#
# Binaries will be look in the path. Make sure your
# path is imported in your session.
# Icons will be looked up from your icon path theme or in
# ~/.local/share/icons/{iconname}.png
#
# There is a cache of the application sorted in ~/.cache/mounch/cache, it is
# used to sort the last one, so the last used appears at the top of the list.

import collections
import os
from  pathlib import Path
import shutil
import subprocess
import sys

import yaml


def menu_command() -> subprocess.Popen:
    """Call and return the subprocess.Open instance to open a menu."""
    if ('XDG_SESSION_TYPE' in os.environ
            and os.environ['XDG_SESSION_TYPE'] == 'wayland'):
        return subprocess.Popen(
                [
                    'wofi',
                    '--dmenu',
                    '--insensitive',
                    '--allow-images',
                    '--prompt="Choose your mounchie:"',
                    # '--style=~/.config/rofi/mounch.rasi',
                ],
                stdout=subprocess.PIPE,
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE)
    else:
        return subprocess.Popen(
                [
                    "rofi", "-dmenu", "-i",
                    "-p", "Choose your mounchie:",
                    "-show-icons",
                    "-no-custom",
                    "-theme", "mounch"
                ],
                stdout=subprocess.PIPE,
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE)


def sort_from_cache(
        application_config: dict,
        cache_file: Path) -> (collections.OrderedDict, dict):
    """Sort the application_config by frequency from the cache.

    Machine learning, big data at work!!!!!
    Sort the application_config by frequency in the
    cache first. It will first do a collection ordering if the element is
    not an empty string when stripped. Sort the cached_entries as list
    sorted by its frequency number and then merge in order as it appears
    in the config (py3.7+) to the one who didn't appear with the other
    application_config dict.

    """
    cached_entries = {}
    for entry in cache_file.read_text().split('\n'):
        try:
            id_, freq_str = entry.strip().split()
            if id_ not in application_config:
                continue
            cached_entries[id_] = int(freq_str)
        except (IndexError, ValueError):
            continue

    application_config = {
        **dict(
            collections.OrderedDict([(el, application_config[el]) for el in dict(
                reversed(
                    sorted(cached_entries.items(),
                           key=lambda item: item[1]))).keys(
            ) if el.strip()])),
        **application_config
    }
    return application_config, cached_entries


def main():
    cache_file = Path("~/.cache/mounch/cache").expanduser()
    configfile = Path("~/.config/mounch/mounch.yaml").expanduser()

    if not configfile.exists():
        print("I could not find config file: ", configfile)
        sys.exit(1)
    application_config = yaml.safe_load(configfile.open('r'))

    if cache_file.exists():
        application_config, cached_entries = sort_from_cache(application_config,
                                                             cache_file)
    else:
        cached_entries = {}

    ret = []
    for config in application_config.values():
        icon = config.get('icon', 'default')
        iconpath = Path(icon).expanduser()
        if iconpath.exists():
            icon = iconpath
        ret.append(f"{config['description']}\0icon\x1f{icon}")

    stringto = '\n'.join(ret).encode()

    popo = menu_command()
    stdout = popo.communicate(input=stringto)[0]
    output = stdout.decode().strip()
    if not output:
        return

    chosen_id = [
        x for x in application_config
        if application_config[x]['description'] == output
    ][0]
    chosen = application_config[chosen_id]

    if not cache_file.parent.exists():
        cache_file.parent.mkdir(0o755)

    if chosen_id not in cached_entries:
        cached_entries[chosen_id] = 0
    else:
        cached_entries[chosen_id] += 1
    cache_file.write_text('\n'.join(
        [f'{entry} {freq}' for entry, freq in cached_entries.items()]))

    binarypath = Path(chosen['binary']).expanduser()
    binary = shutil.which(binarypath)
    if not binary:
        print(f"Cannot find executable \"{chosen['binary']}\"")
        sys.exit(1)

    args = chosen.get('args')

    if args is None:
        os.execv(binary, [binary])
    else:
        if isinstance(args, str):
            args = [args]
        os.execv(binary, [
            binary,
            *args,
        ])


if __name__ == '__main__':
    main()
