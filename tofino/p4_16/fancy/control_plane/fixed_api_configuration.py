

# usage:
# ~/tools/run


sys.path.append("../../bfrt_helper/")

# Loads constants from the p4 file such that i dont have to edit them in both places
import subprocess
from utils import set_ports


# App config
# Fixed API

# stop packet
# with fsm = 1 and fancy.id = 511
p = b'\x00\x01\x02\x03\x04\x05\x88\x88\x88\x88\x88\x01\x08\x01\x01\xff\x02\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00' * 40


# the thing adds 6 bytes so if we want to be able to parse the MAC address we have to do
# what is explained in slides 29 or 30. One trick is to remove 6 bytes and then in the program
# use the Ether DST MAC to match

# period in milliseconds
def enable_packet_gen(period_time=200):
    conn_mgr.pktgen_write_pkt_buffer(0, len(p) - 6, p[6:])
    conn_mgr.pktgen_enable(68)

    # app
    app_cfg = conn_mgr.PktGenAppCfg_t()
    app_cfg.buffer_offset = 0
    app_cfg.length = len(p) - 6
    app_cfg.timer = period * 1000 * 1000  # 200 ms
    app_cfg.batch_count = 0
    app_cfg.pkt_count = 0
    app_cfg.trigger_type = conn_mgr.PktGenTriggerType_t.TIMER_PERIODIC
    #app_cfg.trigger_type = conn_mgr.PktGenTriggerType_t.TIMER_ONE_SHOT
    app_cfg.src_port = 68 & 0b001111111
    conn_mgr.pktgen_cfg_app(0, app_cfg)

    conn_mgr.pktgen_app_enable(0)


def disable_packet_gen():
    # enable app
    conn_mgr.pktgen_app_disable(0)

# conn_mgr.pktgen_app_disable(0)


if __name__ == "__main__":

    #import argparse
    #parser = argparse.ArgumentParser()
    # parser.add_argument('--traffic_gen', action='store_true',
    #                    required=False, default=False)
    # parser.add_argument('--period', help="Packet gen period time in ms",
    #                    type=int, default=200, required=False)
    #
    #args = parser.parse_args()

    print("Configure switch with the Fixed API....")
    # adds ports

    print("Setting switch ports...")
    set_ports(pal, {1: "10G", 3: "100G", 4: "100G",
                    5: "100G", 6: "100G", 7: "100G", 8: "100G"})

    TRAFFIC_GEN = True
    period = 190

    if TRAFFIC_GEN:
        print("Configure packet generator with period {}ms".format(period))
        enable_packet_gen(period_time=period)
