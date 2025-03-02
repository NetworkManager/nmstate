# SPDX-License-Identifier: Apache-2.0

from ctypes import c_int, c_char_p, c_uint32, POINTER, byref, cdll
import json
import logging
import yaml

from .error import (
    NmstateDependencyError,
    NmstateError,
    NmstateInternalError,
    NmstateKernelIntegerRoundedError,
    NmstateNotImplementedError,
    NmstateNotSupportedError,
    NmstatePermissionError,
    NmstatePluginError,
    NmstateValueError,
    NmstateVerificationError,
)

lib = cdll.LoadLibrary("libnmstate.so.2")

lib.nmstate_net_state_retrieve.restype = c_int
lib.nmstate_net_state_retrieve.argtypes = (
    c_uint32,
    POINTER(c_char_p),
    POINTER(c_char_p),
    POINTER(c_char_p),
    POINTER(c_char_p),
)

lib.nmstate_cstring_free.restype = None
lib.nmstate_cstring_free.argtypes = (c_char_p,)

NMSTATE_FLAG_NONE = 0
NMSTATE_FLAG_KERNEL_ONLY = 1 << 1
NMSTATE_FLAG_NO_VERIFY = 1 << 2
NMSTATE_FLAG_INCLUDE_STATUS_DATA = 1 << 3
NMSTATE_FLAG_INCLUDE_SECRETS = 1 << 4
NMSTATE_FLAG_NO_COMMIT = 1 << 5
NMSTATE_FLAG_MEMORY_ONLY = 1 << 6
NMSTATE_FLAG_RUNNING_CONFIG_ONLY = 1 << 7
NMSTATE_PASS = 0


def retrieve_net_state_json(
    kernel_only=False,
    include_status_data=False,
    include_secrets=False,
    running_config_only=False,
):
    c_err_msg = c_char_p()
    c_err_kind = c_char_p()
    c_state = c_char_p()
    c_log = c_char_p()
    flags = NMSTATE_FLAG_NONE
    if kernel_only:
        flags |= NMSTATE_FLAG_KERNEL_ONLY
    if include_status_data:
        flags |= NMSTATE_FLAG_INCLUDE_STATUS_DATA
    if include_secrets:
        flags |= NMSTATE_FLAG_INCLUDE_SECRETS
    if running_config_only:
        flags |= NMSTATE_FLAG_RUNNING_CONFIG_ONLY

    rc = lib.nmstate_net_state_retrieve(
        flags,
        byref(c_state),
        byref(c_log),
        byref(c_err_kind),
        byref(c_err_msg),
    )
    state = c_state.value
    err_msg = c_err_msg.value
    err_kind = c_err_kind.value
    parse_log(c_log.value)
    lib.nmstate_cstring_free(c_log)
    lib.nmstate_cstring_free(c_state)
    lib.nmstate_cstring_free(c_err_kind)
    lib.nmstate_cstring_free(c_err_msg)
    if rc != NMSTATE_PASS:
        raise NmstateError(f"{err_kind}: {err_msg}")
    # pylint: disable=no-member
    return state.decode("utf-8")
    # pylint: enable=no-member


def apply_net_state(
    state,
    kernel_only=False,
    verify_change=True,
    save_to_disk=True,
    commit=True,
    rollback_timeout=60,
):
    c_err_msg = c_char_p()
    c_err_kind = c_char_p()
    c_state = c_char_p(json.dumps(state).encode("utf-8"))
    c_log = c_char_p()
    flags = NMSTATE_FLAG_NONE
    if kernel_only:
        flags |= NMSTATE_FLAG_KERNEL_ONLY

    if not verify_change:
        flags |= NMSTATE_FLAG_NO_VERIFY

    if not commit:
        flags |= NMSTATE_FLAG_NO_COMMIT

    if not save_to_disk:
        flags |= NMSTATE_FLAG_MEMORY_ONLY

    rc = lib.nmstate_net_state_apply(
        flags,
        c_state,
        rollback_timeout,
        byref(c_log),
        byref(c_err_kind),
        byref(c_err_msg),
    )
    err_msg = c_err_msg.value
    err_kind = c_err_kind.value
    parse_log(c_log.value)
    lib.nmstate_cstring_free(c_log)
    lib.nmstate_cstring_free(c_err_kind)
    lib.nmstate_cstring_free(c_err_msg)
    if rc != NMSTATE_PASS:
        raise map_error(err_kind, err_msg)


def commit_checkpoint(checkpoint):
    c_err_msg = c_char_p()
    c_err_kind = c_char_p()
    c_checkpoint = c_char_p(checkpoint)
    c_log = c_char_p()

    rc = lib.nmstate_checkpoint_commit(
        c_checkpoint,
        byref(c_log),
        byref(c_err_kind),
        byref(c_err_msg),
    )

    err_msg = c_err_msg.value
    err_kind = c_err_kind.value
    parse_log(c_log.value)
    lib.nmstate_cstring_free(c_log)
    lib.nmstate_cstring_free(c_err_kind)
    lib.nmstate_cstring_free(c_err_msg)
    if rc != NMSTATE_PASS:
        raise map_error(err_kind, err_msg)


def rollback_checkpoint(checkpoint):
    c_err_msg = c_char_p()
    c_err_kind = c_char_p()
    c_checkpoint = c_char_p(checkpoint)
    c_log = c_char_p()

    rc = lib.nmstate_checkpoint_rollback(
        c_checkpoint,
        byref(c_log),
        byref(c_err_kind),
        byref(c_err_msg),
    )

    err_msg = c_err_msg.value
    err_kind = c_err_kind.value
    parse_log(c_log.value)
    lib.nmstate_cstring_free(c_log)
    lib.nmstate_cstring_free(c_err_kind)
    lib.nmstate_cstring_free(c_err_msg)
    if rc != NMSTATE_PASS:
        raise map_error(err_kind, err_msg)


def gen_conf(state):
    c_err_msg = c_char_p()
    c_err_kind = c_char_p()
    c_state = c_char_p(json.dumps(state).encode("utf-8"))
    c_configs = c_char_p()
    c_log = c_char_p()
    rc = lib.nmstate_generate_configurations(
        c_state,
        byref(c_configs),
        byref(c_log),
        byref(c_err_kind),
        byref(c_err_msg),
    )
    configs = c_configs.value
    err_msg = c_err_msg.value
    err_kind = c_err_kind.value
    parse_log(c_log.value)
    lib.nmstate_cstring_free(c_log)
    lib.nmstate_cstring_free(c_err_kind)
    lib.nmstate_cstring_free(c_err_msg)
    if rc != NMSTATE_PASS:
        raise map_error(err_kind, err_msg)
    # pylint: disable=no-member
    return configs.decode("utf-8")
    # pylint: enable=no-member


def gen_diff(new_state, old_state):
    c_err_msg = c_char_p()
    c_err_kind = c_char_p()
    c_new_state = c_char_p(json.dumps(new_state).encode("utf-8"))
    c_old_state = c_char_p(json.dumps(old_state).encode("utf-8"))
    c_diff_state = c_char_p()
    rc = lib.nmstate_generate_differences(
        c_new_state,
        c_old_state,
        byref(c_diff_state),
        byref(c_err_kind),
        byref(c_err_msg),
    )
    diff_state = c_diff_state.value
    err_msg = c_err_msg.value
    err_kind = c_err_kind.value
    lib.nmstate_cstring_free(c_err_kind)
    lib.nmstate_cstring_free(c_err_msg)
    if rc != NMSTATE_PASS:
        raise map_error(err_kind, err_msg)
    # pylint: disable=no-member
    return diff_state.decode("utf-8")
    # pylint: enable=no-member


def net_state_serialize(state, use_yaml=True):
    c_err_msg = c_char_p()
    c_err_kind = c_char_p()
    if use_yaml:
        c_state = c_char_p(yaml.dump(state).encode("utf-8"))
    else:
        c_state = c_char_p(json.dumps(state).encode("utf-8"))
    c_formated_state = c_char_p()
    rc = lib.nmstate_net_state_format(
        c_state,
        byref(c_formated_state),
        byref(c_err_kind),
        byref(c_err_msg),
    )
    formated_state = c_formated_state.value
    err_msg = c_err_msg.value
    err_kind = c_err_kind.value
    lib.nmstate_cstring_free(c_err_kind)
    lib.nmstate_cstring_free(c_err_msg)
    if rc != NMSTATE_PASS:
        raise map_error(err_kind, err_msg)
    # pylint: disable=no-member
    return formated_state.decode("utf-8")
    # pylint: enable=no-member


def net_state_from_policy(policy, cur_state):
    c_err_msg = c_char_p()
    c_err_kind = c_char_p()
    c_policy = c_char_p(json.dumps(policy).encode("utf-8"))
    c_cur_state = c_char_p(json.dumps(cur_state).encode("utf-8"))
    c_state = c_char_p()
    c_log = c_char_p()
    rc = lib.nmstate_net_state_from_policy(
        c_policy,
        c_cur_state,
        byref(c_state),
        byref(c_log),
        byref(c_err_kind),
        byref(c_err_msg),
    )
    state = c_state.value
    err_msg = c_err_msg.value
    err_kind = c_err_kind.value
    parse_log(c_log.value)
    lib.nmstate_cstring_free(c_log)
    lib.nmstate_cstring_free(c_err_kind)
    lib.nmstate_cstring_free(c_err_msg)
    if rc != NMSTATE_PASS:
        raise map_error(err_kind, err_msg)
    # pylint: disable=no-member
    return state.decode("utf-8")
    # pylint: enable=no-member


def map_error(err_kind, err_msg):
    err_msg = err_msg.decode("utf-8")
    err_kind = err_kind.decode("utf-8")
    if err_kind == "VerificationError":
        return NmstateVerificationError(err_msg)
    elif err_kind == "InvalidArgument":
        return NmstateValueError(err_msg)
    elif err_kind == "Bug":
        return NmstateInternalError(err_msg)
    elif err_kind == "PluginFailure":
        return NmstatePluginError(err_msg)
    elif err_kind == "NotImplementedError":
        return NmstateNotImplementedError(err_msg)
    elif err_kind == "KernelIntegerRoundedError":
        return NmstateKernelIntegerRoundedError(err_msg)
    elif err_kind == "NotSupportedError":
        return NmstateNotSupportedError(err_msg)
    elif err_kind == "DependencyError":
        return NmstateDependencyError(err_msg)
    elif err_kind == "PermissionError":
        return NmstatePermissionError(err_msg)
    else:
        return NmstateError(f"{err_kind}: {err_msg}")


def parse_log(logs):
    if logs is None:
        return

    log_entries = []
    try:
        log_entries = json.loads(logs.decode("utf-8"))
    except Exception:
        pass
    for log_entry in log_entries:
        msg = f"{log_entry['time']}:{log_entry['file']}: {log_entry['msg']}"
        level = log_entry["level"]

        if level == "ERROR":
            logging.error(msg)
        elif level == "WARN":
            logging.warning(msg)
        elif level == "INFO":
            logging.info(msg)
        else:
            logging.debug(msg)
