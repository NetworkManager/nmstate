# SPDX-License-Identifier: LGPL-2.1-or-later

import os
from contextlib import contextmanager
import time

import libnmstate
from libnmstate.schema import DNS
from libnmstate.schema import Interface
from libnmstate.schema import InterfaceState

from .cmdlib import exec_cmd

NM_CONN_FOLDER = "/etc/NetworkManager/system-connections"


@contextmanager
def gen_conf_apply(desire_state):
    iface_names = [
        iface[Interface.NAME] for iface in desire_state.get(Interface.KEY, [])
    ]
    file_paths = []
    try:
        conns = libnmstate.generate_configurations(desire_state).get(
            "NetworkManager", []
        )
        for conn in conns:
            file_paths.append(save_nmconnection(conn[0], conn[1]))
        reload_nm_connection()
        yield
    finally:
        absent_state = {
            Interface.KEY: [],
            DNS.KEY: {DNS.CONFIG: {DNS.SERVER: [], DNS.SEARCH: []}},
        }
        for iface_name in iface_names:
            absent_state[Interface.KEY].append(
                {
                    Interface.NAME: iface_name,
                    Interface.STATE: InterfaceState.ABSENT,
                }
            )
        libnmstate.apply(absent_state, verify_change=False)
        for file_path in file_paths:
            try:
                os.unlink(file_path)
            except Exception:
                pass


def save_nmconnection(file_name, content):
    file_path = f"{NM_CONN_FOLDER}/{file_name}"
    with open(file_path, "w") as fd:
        fd.write(content)

    os.chmod(file_path, 0o600)
    os.chown(file_path, 0, 0)
    return file_path


def reload_nm_connection():
    exec_cmd("nmcli c reload".split(), check=True)
    # Wait NetworkManager to activate the connections
    time.sleep(5)