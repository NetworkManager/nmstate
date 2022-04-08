#
# Copyright (c) 2018-2020 Red Hat, Inc.
#
# This file is part of nmstate
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 2.1 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
from unittest import mock

import pytest

from libnmstate import nm


@pytest.fixture()
def client_mock():
    yield mock.MagicMock()


def test_list_devices(client_mock):
    nm.device.list_devices(client_mock)

    client_mock.get_devices.assert_called_once()


def test_get_device_common_info():
    dev = mock.MagicMock()

    info = nm.device.get_device_common_info(dev)

    expected_info = {
        "name": dev.get_iface.return_value,
        "type_id": dev.get_device_type.return_value,
        "type_name": dev.get_type_description.return_value,
        "state": dev.get_state.return_value,
    }
    assert expected_info == info