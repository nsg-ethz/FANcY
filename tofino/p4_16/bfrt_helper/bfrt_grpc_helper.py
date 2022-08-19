#!/usr/bin/python3

import os
import sys
from tabulate import tabulate
#
# This is optional if you use proper PYTHONPATH
#
SDE_INSTALL = os.environ['SDE_INSTALL']

PYTHON3_VER = '{}.{}'.format(
    sys.version_info.major,
    sys.version_info.minor)
SDE_PYTHON3 = os.path.join(SDE_INSTALL, 'lib', 'python' + PYTHON3_VER,
                           'site-packages')

sys.path.append(SDE_PYTHON3)
sys.path.append(os.path.join(SDE_PYTHON3, 'tofino'))
sys.path.append(os.path.join(SDE_PYTHON3, 'tofino', 'bfrt_grpc'))


import bfrt_grpc.client as gc


class BfRtAPI:
    """Sets up connection to gRPC server and bind.

    Args:
        grpc_addr (str)                               : gRPC address and port to connect to
        client_id (int)                               : Client ID
        p4_name (str)                                 : Name of P4 program. If none is given,
                                                        then the test performs a bfrt_info_get() and binds to the first
                                                        P4 that comes as part of the bfrt_info_get()
        notifications (bfrt_grpc.client.Notifications): A Notifications object.
        perform_bind (bool)                           : Set this to **False** if binding is not required
        timeout (int or float)                        : Timeout to wait for connection
        num_tries (int)                               : Number of connection tries
        perform_subscribe (bool)                      : Set this to **False** if client does not need to
                                                        subscribe for any notifications
        target (bfrt_grpc.client.Target)              : Target to use for the APIs

    Returns:
        tuple: ``(interface, bfrt_info)`` where ``interface`` is the client interface
        and ``bfrt_info`` is a :py:class:`~bfrt_grpc.client._BfRtInfo` containing all
        the information of the P4 program installed in the switch.

    Note:
        If you need to disable any notifications, then do the below as example::

            Notifications(enable_learn=False)

        Otherwise default value is sent as below::

            enable_learn = True
            enable_idletimeout = True
            enable_port_status_change = True
    """

    def __init__(self, grpc_addr='localhost:50052',
                 client_id=0,
                 p4_name=None,
                 notifications=None,
                 perform_bind=True,
                 timeout=1,
                 num_tries=5,
                 perform_subscribe=True,
                 target=gc.Target()):

        if perform_bind and not perform_subscribe:
            raise RuntimeError(
                "perform_bind must be equal to perform_subscribe")

        self.bfrt_info = None

        self.interface = gc.ClientInterface(
            grpc_addr, client_id=client_id, device_id=0,
            notifications=notifications, timeout=timeout, num_tries=num_tries,
            perform_subscribe=perform_subscribe)

        # If p4_name wasn't specified, then perform a bfrt_info_get and set p4_name
        # to it
        if not p4_name:
            self.bfrt_info = self.interface.bfrt_info_get()
            self.p4_name = self.bfrt_info.p4_name_get()

        # Set forwarding pipeline config (For the time being we are just
        # associating a client with a p4). Currently the grpc server supports
        # only one client to be in-charge of one p4.
        if perform_bind:
            self.interface.bind_pipeline_config(self.p4_name)

        # Set default target
        self.set_target(target)

    def __getattr__(self, name):
        """Adds methods from the :py:class:`bfrt_grpc.client.ClientInterface` class."""
        return getattr(self.interface, name)

    def set_target(self, target=gc.Target()):
        """Sets Target for the APIs.

        Args:
            target (bfrt_grpc.client.Target): Target to use for the APIs
        """
        self.target = target

    def print_tables_info(self):
        # Print the list of tables in the "pipe" node
        dev_tgt = self.target

        data = []
        for name in self.bfrt_info.table_dict.keys():
            if name.split('.')[0] == 'pipe':
                # pdb.set_trace()
                t = self.bfrt_info.table_get(name)
                table_name = t.info.name_get()
                if table_name != name:
                    continue
                table_type = t.info.type_get()
                try:
                    result = t.usage_get(dev_tgt)
                    table_usage = next(result)
                except:
                    table_usage = 'n/a'
                table_size = t.info.size_get()
                data.append([table_name, table_type, table_usage, table_size])

        print(
            tabulate(
                data,
                headers=['Full Table Name', 'Type', 'Usage', 'Capacity']))

    def print_table_info(self, table_name):

        print("====Table Info===")
        t = self.bfrt_info.table_get(table_name)
        print("{:<30}: {}".format("TableName", t.info.name_get()))
        print("{:<30}: {}".format("Size", t.info.size_get()))
        print("{:<30}: {}".format("Actions", t.info.action_name_list_get()))
        print("{:<30}:".format("KeyFields"))
        for field in sorted(t.info.key_field_name_list_get()):
            print("  {:<28}: {} => {}".format(
                field, t.info.key_field_type_get(field),
                t.info.key_field_match_type_get(field)))
        print("{:<30}:".format("DataFields"))
        for field in t.info.data_field_name_list_get():
            print("  {:<28}: {} {}".format(
                "{} ({})".format(field, t.info.data_field_id_get(field)),
                t.info.data_field_type_get(field),
                t.info.data_field_size_get(field),
            ))
        print("================")

    def clear_table(self, table_name):
        """clear a table"""
        t = self.bfrt_info.table_get(table_name)
        # remove all entries
        # set default again
        try:
            t.entry_del(self.target, [])
        except:
            print("Problem clearing {}".format(table_name))
            pass

        # check table type
        table_type = t.info.type_get()
        if "MatchAction" in table_type:
            try:
                t.default_entry_reset(self.target)
            except:
                pass

    def clear_all(self):
        self.clear_tables()
        self.clear_mirroring()

    def clear_tables(self, node="pipe"):
        """Clears tables and registers"""
        tables = self.bfrt_info.table_dict.keys()
        for table_name in tables:
            if table_name.split(".")[0] == node:
                self.clear_table(table_name)

    def dump_table(self, table_name):
        """Print all table entries"""
        table = self.bfrt_info.table_get(table_name)
        for (data, key) in table.entry_get(self.target):
            print(key.to_dict(), data.to_dict())

    def entry_add(self, table_name, keys=[], data=[], action_name=None):
        """Adds entry to table.

        Args:
            table_name (str)         : Name of the table
            keys (list)              : List of tuples ``(key_name, key_value)``
            data (list)              : List of tuples ``(data_name, data_value)``
            action_name (str or None): Name of the action to execute
        """
        table = self.bfrt_info.table_get(table_name)
        _keys = table.make_key([gc.KeyTuple(*k) for k in keys])
        _data = table.make_data(
            [gc.DataTuple(*d) for d in data], action_name)

        table.entry_add(
            self.target,
            [_keys],
            [_data]
        )

    def add_mirroring(self, eg_port, session_id, direction="BOTH"):
        """configures mirroring session"""

        table = self.bfrt_info.table_get('$mirror.cfg')

        keys = [('$sid', session_id)]
        _keys = table.make_key([gc.KeyTuple(*k) for k in keys])

        _data = table.make_data([
            gc.DataTuple('$direction', str_val=direction),
            gc.DataTuple('$session_enable', bool_val=True),
            gc.DataTuple('$ucast_egress_port', eg_port),
            gc.DataTuple('$egress_port_queue', 1),
            gc.DataTuple('$ucast_egress_port_valid', bool_val=True)
        ], "$normal")

        table.entry_add(
            self.target,
            [_keys],
            [_data]
        )

    def clear_mirroring(self):
        """clears all mirroring sessions"""

        table = self.bfrt_info.table_get('$mirror.cfg')
        for (data, key) in table.entry_get(self.target):
            keys = [('$sid', key.to_dict()["$sid"]["value"])]
            _keys = table.make_key([gc.KeyTuple(*k) for k in keys])
            table.entry_del(self.target, [_keys])

    def entry_del(self, table_name, keys=[]):
        """Adds entry to table.

        Args:
           table_name (str)         : Name of the table
           keys (list)              : List of tuples ``(key_name, key_value)``
        """
        table = self.bfrt_info.table_get(table_name)
        _keys = table.make_key([gc.KeyTuple(*k) for k in keys])

        table.entry_del(
            self.target,
            [_keys],
        )

    def entry_mod(
            self, table_name, keys=[],
            data=[],
            action_name=None, flags={"reset_ttl": True}):
        """Modifies entry of a table.

        Args:
           table_name (str)         : Name of the table
           keys (list)              : List of tuples ``(key_name, key_value)``
           data (list)              : List of tuples ``(data_name, data_value)``
           action_name (str or None): Name of the action to execute
           flags (dict)             : Dictionary of modify flags.

        Note:
            Possible **flags** are the following:
            - ``from_hw`` (:py:class:`bool`),
            - ``key_only`` (:py:class:`bool`),
            - ``mod_del`` (:py:class:`bool`),
            - ``reset_ttl`` (:py:class:`bool`).
        """
        table = self.bfrt_info.table_get(table_name)
        _keys = table.make_key([gc.KeyTuple(*k) for k in keys])
        _data = table.make_data(
            [gc.DataTuple(*d) for d in data], action_name)

        table.entry_mod(
            self.target,
            [_keys],
            [_data],
            flags=flags
        )

    def entry_get(self, table_name, keys=[], flags={"from_hw": True}):
        """Gets entry from a table.

        Args:
           table_name (str)         : Name of the table
           keys (list)              : List of tuples ``(key_name, key_value)``
           flags (dict)             : Dictionary of modify flags.

        Note:
            Possible **flags** are the following:
            - ``from_hw`` (:py:class:`bool`),
            - ``key_only`` (:py:class:`bool`),
            - ``mod_del`` (:py:class:`bool`),
            - ``reset_ttl`` (:py:class:`bool`).
        """
        table = self.bfrt_info.table_get(table_name)
        _keys = table.make_key([gc.KeyTuple(*k) for k in keys])
        data, _ = next(table.entry_get(
            self.target,
            [
                _keys
            ],
            flags=flags
        ))

        return data.to_dict()

    def default_entry_set(self, table_name, data=[], action_name=None):
        """Sets default entry of a table.

        Args:
           table_name (str)         : Name of the table
           data (list)              : List of tuples ``(data_name, data_value)``
           action_name (str or None): Name of the action to execute
        """
        table = self.bfrt_info.table_get(table_name)
        _data = table.make_data(
            [gc.DataTuple(*d) for d in data], action_name)

        table.default_entry_set(
            self.target,
            _data
        )

    def default_entry_reset(self, table_name):
        """Adds entry to table.

        Args:
           table_name (str)         : Name of the table
        """
        table = self.bfrt_info.table_get(table_name)
        table.default_entry_reset(
            self.target
        )

    # Register oriented helpers

    def register_entry_get(self, reg_name, index, flags={"from_hw": True}):
        """Reads one register entry"""

        table = self.bfrt_info.table_get(reg_name)
        _keys = table.make_key([gc.KeyTuple("$REGISTER_INDEX", index)])
        data, _ = next(table.entry_get(
            self.target,
            [
                _keys
            ],
            flags=flags
        ))
        data_name = table.info.data_dict_allname["f1"]
        return data.to_dict()[data_name]

    def register_entry_range_get(
            self, reg_name, start, end, flags={"from_hw": True}):
        "Reads multiple register entryes"
        entries = []
        for i in range(start, end):
            entries.append(self.register_entry_get(reg_name, i, flags))
        return entries

    def register_entry_add(self, reg_name, index, value):
        """Reads one register entry"""

        table = self.bfrt_info.table_get(reg_name)

        _keys = table.make_key([gc.KeyTuple("$REGISTER_INDEX", index)])
        data_name = table.info.data_dict_allname["f1"]
        _data = table.make_data([gc.DataTuple(data_name, value)])

        table.entry_add(self.target, [_keys], [_data])

    # Ports Helpers
    # Traffic Manager Helpers

    # Traffic Generator Helpers
