#
# port forwarding
# We run this from the gateway
# ssh -f -N -L 0.0.0.0:5000:tofino1:5000 nsg@tofino1
# ssh -f -N -L 0.0.0.0:5001:tofino4:5001 nsg@tofino4

from server import ClientTCP
from server_mappings_private import remote_mappings

import multiprocessing
import subprocess
import time
import socket

STOP_MSG = b'\x00\x01\x02\x03\x04\x05\x88\x88\x88\x88\x88\x01\x08\x01\x01\xff\x02\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00' * 40


def send_stop_raw(iface, interval=None, random_sleep=0):
    # sleeps some random time to add randomness to the zooming speed
    if random_sleep:
        time.sleep(random_sleep)
    try:
        s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
        s.bind((iface, socket.SOCK_RAW))

        if interval:
            while True:
                now = time.time()
                s.send(STOP_MSG)
                time.sleep(interval - (time.time() - now))
        else:
            s.send(STOP_MSG)
    except e:
        print(e)
        print("Either the interface {} does not exist or you do not have sudo privileges.".format(iface))

    finally:
        s.close()


def get_iperf_bw(bw, tcp_share, num_tcp_flows, num_udp_flows=1):
    """gets the bandwidth in mb for each flow, udp and tcp, given some traffic share in %"""
    tcp_bw = bw * tcp_share
    udp_bw = bw * (1 - tcp_share)
    per_flow_tcp_bw = tcp_bw / num_tcp_flows
    per_flow_udp_bw = udp_bw / num_udp_flows
    return per_flow_tcp_bw, per_flow_udp_bw


# bw in MB
def run_tofino_zooming_eval(
        output_dir, ips_setup, sender_intf, remote_server="receiver",
        bw=1000, duration=10, failure_time=4, tcp_bw_share=0.99,
        num_tcp_flows=10, loss_rate=1, zooming_speed=0.2, write_interval=0.01):

    sender_client = ClientTCP(remote_mappings[remote_server])
    tofino1_client = ClientTCP(remote_mappings["tofino1"])
    tofino4_client = ClientTCP(remote_mappings["tofino4"])

    # create output dir
    out_path = output_dir
    subprocess.call("mkdir -p {}".format(out_path), shell=True)
    # make a remote directory
    sender_client.send({"bash_cmd": "mkdir -p {}".format(out_path)})

    # kill iperf servers
    sender_client.send({"bash_cmd": "killall iperf"})

    # kill iperf clients
    subprocess.Popen("killall iperf", shell=True)

    # set loss rate to 0 for all ips
    for ip, _ in ips_setup:
        tofino4_client.send(
            {"controller_cmd": 'self.controller.set_loss_rate("{}", 1, 0)'.format(ip)})

    # clear bloom filters
    tofino1_client.send({"controller_cmd": 'self.controller.configure_all()'})
    tofino1_client.send(
        {"controller_cmd": 'self.controller.controller.clear_table("packet_to_id")'})

    # tofino1_client.send(
    #    {"controller_cmd": 'self.controller.clean_bloom_filters()'})

    # small wait
    time.sleep(3)

    # start iperf servers
    print("start servers")
    for ip, port in ips_setup:
        # tcp and udp
        udp_name = out_path + "receiver_udp_{}_{}_{}_{}_{}.txt".format(
            ip, port, bw, loss_rate, zooming_speed)
        tcp_name = out_path + "receiver_tcp_{}_{}_{}_{}_{}.txt".format(
            ip, port, bw, loss_rate, zooming_speed)
        udp_cmd = "iperf -s -p {} -i {} -e -u -o {}".format(
            port, write_interval, udp_name)
        tcp_cmd = "iperf -s -p {} -i {} -e --sum-only -o {} ".format(
            port, write_interval, tcp_name)
        print(udp_cmd)
        print(tcp_cmd)
        sender_client.send({"bash_cmd": udp_cmd})
        sender_client.send({"bash_cmd": tcp_cmd})

    time.sleep(2)

    # start iperf clients
    per_flow_tcp_bw, per_flow_udp_bw = get_iperf_bw(
        bw, tcp_bw_share, num_tcp_flows)

    traffic_ts = time.time()
    print("start flows")
    for ip, port in ips_setup:
        udp_name = out_path + "sender_udp_{}_{}_{}_{}_{}.txt".format(
            ip, port, bw, loss_rate, zooming_speed)
        tcp_name = out_path + "sender_tcp_{}_{}_{}_{}_{}.txt".format(
            ip, port, bw, loss_rate, zooming_speed)
        udp_cmd = "iperf -c {} -p {} -t {} -i {} -e  -u -b {}M -l 64 -o {}".format(
            ip, port, duration, write_interval, per_flow_udp_bw, udp_name)
        tcp_cmd = "iperf -c {} -p {} -t {} -i {} -e -P {} -b {}M --sum-only -o {}".format(
            ip, port, duration, write_interval, num_tcp_flows, per_flow_tcp_bw, tcp_name)
        print(udp_cmd)
        print(tcp_cmd)
        subprocess.Popen(udp_cmd, shell=True)
        subprocess.Popen(tcp_cmd, shell=True)

    # start the zooming packet pusher
    # p = multiprocessing.Process(target=send_stop_raw, args=(
    #    sender_intf, zooming_speed, 0))
    # p.start()

    # wait
    time.sleep(failure_time)
    fail_ts = time.time()

    # fail
    print("Link loss rate ->  {}".format(loss_rate))
    for ip, _ in ips_setup:
        tofino4_client.send(
            {"controller_cmd": 'self.controller.set_loss_rate("{}", 1, {})'.format(ip, loss_rate)})

    # wait
    time.sleep(duration - failure_time + 2)

    # clean

    print("clean all")
    # set loss rate to 0 for all ips
    for ip, _ in ips_setup:
        tofino4_client.send(
            {"controller_cmd": 'self.controller.set_loss_rate("{}", 1, 0)'.format(ip)})

    # clear bloom filters
    tofino1_client.send({"controller_cmd": 'self.controller.configure_all()'})
    # remove entries so all go to zooming
    tofino1_client.send(
        {"controller_cmd": 'self.controller.controller.clear_table("packet_to_id")'})
    # tofino1_client.send(
    #    {"controller_cmd": 'self.controller.clean_bloom_filters()'})

    # kill iperf servers
    sender_client.send({"bash_cmd": "killall iperf"})

    # kill iperf clients
    subprocess.Popen("killall iperf", shell=True)

    # stop zooming
    # p.terminate()

    # save timestamps
    print("save ts")
    out_file = out_path + "ts_{}_{}_{}.txt".format(
        bw, loss_rate, zooming_speed)
    with open(out_file, "w") as f:
        f.write(str(traffic_ts) + "\n")
        f.write(str(fail_ts) + "\n")

    time.sleep(2)


def run_multiple_zooming_evals(
        output_dir, ips_setup, sender_intf, remote_server, loss_rates,
        prefix_bw, zooming_speed):

    # several parameters are hardcoded, for the eval is fine. Otherwise this
    # function needs to be changed by adding more parameters.

    for bw in prefix_bw:
        for loss_rate in loss_rates:
            print("Start zooming test {} {}".format(bw, loss_rate))
            run_tofino_zooming_eval(
                output_dir, ips_setup, sender_intf, remote_server, bw=bw,
                duration=6, failure_time=2, tcp_bw_share=0.999,
                num_tcp_flows=10, loss_rate=loss_rate,
                zooming_speed=zooming_speed, write_interval=0.05)
            time.sleep(4)


# bw in MB
def run_tofino_dedicated_eval(
        output_dir, ips_setup, remote_server="receiver", bw=1000, duration=10,
        failure_time=4, tcp_bw_share=0.99, num_tcp_flows=10, loss_rate=1,
        write_interval=0.01, timeout=0.2):

    # connect to remote server (Receiver)
    sender_client = ClientTCP(remote_mappings[remote_server])
    tofino1_client = ClientTCP(remote_mappings["tofino1"])
    tofino4_client = ClientTCP(remote_mappings["tofino4"])

    # create output dir
    out_path = output_dir
    subprocess.call("mkdir -p {}".format(out_path), shell=True)
    sender_client.send({"bash_cmd": "mkdir -p {}".format(out_path)})

    # kill iperf servers
    sender_client.send({"bash_cmd": "killall iperf"})

    # kill iperf clients
    subprocess.Popen("killall iperf", shell=True)

    # set loss rate to 0 for all ips
    for ip, _ in ips_setup:
        tofino4_client.send(
            {"controller_cmd": 'self.controller.set_loss_rate("{}", 1, 0)'.format(ip)})

    time.sleep(3)

    # start iperf servers
    print("start servers")
    for ip, port in ips_setup:
        # tcp and udp
        udp_name = out_path + "receiver_udp_{}_{}_{}_{}.txt".format(
            ip, port, bw, loss_rate)
        tcp_name = out_path + "receiver_tcp_{}_{}_{}_{}.txt".format(
            ip, port, bw, loss_rate)
        udp_cmd = "iperf -s -p {} -i {} -e -u -o {}".format(
            port, write_interval, udp_name)
        tcp_cmd = "iperf -s -p {} -i {} -e --sum-only -o {} ".format(
            port, write_interval, tcp_name)
        print(udp_cmd)
        print(tcp_cmd)
        sender_client.send({"bash_cmd": udp_cmd})
        sender_client.send({"bash_cmd": tcp_cmd})

    # start iperf clients
    per_flow_tcp_bw, per_flow_udp_bw = get_iperf_bw(
        bw, tcp_bw_share, num_tcp_flows)

    # set packet count depending on the bw
    udp_1_64 = 2048
    pkts_timer = (per_flow_udp_bw * 2048 * timeout)  # Timeout time
    print("Packets timer {}".format(pkts_timer))

    tofino1_client.send(
        {"controller_cmd": 'self.controller.modify_num_packet_count({})'.format(int(pkts_timer))})
    # clear bloom filters
    tofino1_client.send({"controller_cmd": 'self.controller.configure_all()'})

    time.sleep(4)

    traffic_ts = time.time()
    print("start flows")
    for ip, port in ips_setup:
        udp_name = out_path + "sender_udp_{}_{}_{}_{}.txt".format(
            ip, port, bw, loss_rate)
        tcp_name = out_path + "sender_tcp_{}_{}_{}_{}.txt".format(
            ip, port, bw, loss_rate)
        udp_cmd = "iperf -c {} -p {} -t {} -i {} -e  -u -b {}M -l 64 -o {}".format(
            ip, port, duration, write_interval, per_flow_udp_bw, udp_name)
        tcp_cmd = "iperf -c {} -p {} -t {} -i {} -e -P {} -b {}M --sum-only -o {}".format(
            ip, port, duration, write_interval, num_tcp_flows, per_flow_tcp_bw, tcp_name)
        print(udp_cmd)
        print(tcp_cmd)
        subprocess.Popen(udp_cmd, shell=True)
        subprocess.Popen(tcp_cmd, shell=True)

    # wait
    time.sleep(failure_time)
    fail_ts = time.time()

    # fail
    print("Link loss rate ->  {}".format(loss_rate))
    # set loss rate for all ips
    for ip, _ in ips_setup:
        tofino4_client.send(
            {"controller_cmd": 'self.controller.set_loss_rate("{}", 1, {})'.format(ip, loss_rate)})

    # wait
    time.sleep(duration - failure_time + 2)

    # clean
    print("clean all")
    # set loss rate to 0 for all ips
    for ip, _ in ips_setup:
        tofino4_client.send(
            {"controller_cmd": 'self.controller.set_loss_rate("{}", 1, 0)'.format(ip)})

    # clear bloom filters
    tofino1_client.send({"controller_cmd": 'self.controller.configure_all()'})

    # kill iperf servers
    sender_client.send({"bash_cmd": "killall iperf"})

    # kill iperf clients
    subprocess.Popen("killall iperf", shell=True)

    # save timestamps
    print("save ts")
    out_file = out_path + "ts_{}_{}.txt".format(bw, loss_rate)
    with open(out_file, "w") as f:
        f.write(str(traffic_ts) + "\n")
        f.write(str(fail_ts) + "\n")

    time.sleep(2)


def run_multiple_dedicated_evals(
        output_dir, ips_setup, remote_server, loss_rates, prefix_bw, timeout):

    # several parameters are hardcoded, for the eval is fine. Otherwise this
    # function needs to be changed by adding more parameters.

    # create output dir
    for bw in prefix_bw:
        for loss_rate in loss_rates:
            print("Start dedicated test {} {}".format(bw, loss_rate))
            run_tofino_dedicated_eval(
                output_dir, ips_setup, remote_server, bw=bw, duration=6,
                failure_time=2, tcp_bw_share=0.999, num_tcp_flows=10,
                loss_rate=loss_rate, write_interval=0.05, timeout=timeout)
            time.sleep(4)


if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--test_type', help="Test type: dedicated or zooming",
        type=str, required=False, default="dedicated")
    parser.add_argument(
        '--output_dir', help="Path to experiment's outputs",
        type=str, required=True, default="")
    parser.add_argument(
        '--remote_server',
        help="Name of the remote server matching server mappings", type=str,
        required=False, default="receiver")
    parser.add_argument(
        '--sender_intf',
        help="Name of the interface used by the sender to send traffic",
        type=str, required=False, default="enp129s0f0")

    args = parser.parse_args()

    # Some hardcoded parameters
    loss_rates = [0.01, 0.1, 1]
    # With iperf I do not manage to send more than ~50Gbps per interface.
    prefix_bw = [50000]
    ips_setup = [("11.0.2.2", 31000)]

    if args.test_type == "dedicated":
        run_multiple_dedicated_evals(
            args.output_dir, ips_setup, args.remote_server,
            loss_rates, prefix_bw, 0.2)

    else:
        run_multiple_zooming_evals(
            args.output_dir, ips_setup, args.sender_intf,
            args.remote_server, loss_rates, prefix_bw, 0.19)
