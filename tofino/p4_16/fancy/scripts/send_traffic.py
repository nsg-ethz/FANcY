#!/usr/bin/env python
import sys
import socket
import time
from threading import Thread, Event
from scapy.all import *
from fancy_scapy import actions, reverse_actions, FANCY, print_packet, IPV4, _FANCY, FANCY_COUNTER, FANCY_LENGTH

STOP_MSG = '\x00\x01\x02\x03\x04\x05\x88\x88\x88\x88\x88\x88\x08\x01\x00\x00"\x00\x00\x00\x00\x00\x00\x00\x00'


def print_packet(packet):
    print("[!] A packet was reflected from the switch: ")
    # packet.show()
    ether_layer = packet.getlayer(Ether)
    print(
        "[!] Info: {src} -> {dst}\n".format(src=ether_layer.src, dst=ether_layer.dst))


def print_fancy_packet(packet):
    # packet.show()
    ether_layer = packet.getlayer(Ether)

    if ether_layer.type == 0x801:
        fancy = packet.getlayer(FANCY)
        print("ACTION = {} \nACK = {}".format(
            reverse_actions[fancy.action], fancy.ack))

    else:
        print(packet)


class Sniffer(Thread):
    def __init__(self, interface="veth0", print_func=print_packet):

        super(Sniffer, self).__init__()

        self.interface = interface
        self.my_mac = get_if_hwaddr(interface)
        print(self.my_mac)
        self.daemon = True
        self.print_packet = print_func
        self.socket = None
        self.stop_sniffer = Event()

    def isNotOutgoing(self, pkt):
        return pkt[Ether].src != self.my_mac

    def run(self):

        self.socket = conf.L2listen(
            type=ETH_P_ALL,
            iface=self.interface
        )

        sniff(opened_socket=self.socket, prn=self.print_packet,
              lfilter=self.isNotOutgoing, stop_filter=self.should_stop_sniffer)

    def join(self, timeout=None):
        self.stop_sniffer.set()
        super(Sniffer, self).join(timeout)

    def should_stop_sniffer(self, packet):
        return self.stop_sniffer.isSet()


def get_if():
    ifs = get_if_list()
    iface = None  # "h1-eth0"
    for i in get_if_list():
        if "eth0" in i:
            iface = i
            break
    if not iface:
        print("Cannot find eth0 interface")
        exit(1)
    return iface


def send_packet(iface, addr="10.10.10.10", count=1, delay=0, tos=0):
    for i in range(count):
        pkt = Ether(src="88:88:88:88:88:01", dst='00:01:02:03:04:05')
        pkt = pkt / IP(dst=addr, tos=((tos + i) % 256)) / ("A" * 40)
        sendp(pkt, iface=iface, verbose=False)
        time.sleep(delay)


def send_fancy_packet(
        iface, action, count, ack, fsm, counter_value=0, number=1, delay=0,
        multiple_counters=None, mlength=32, id=0):
    print("Sending {} packets to {}".format(number, iface))
    pkt = Ether(src="88:88:88:88:88:01", dst='00:01:02:03:04:05', type=_FANCY)
    pkt = pkt / FANCY(id=id, count_flag=count, ack=ack, fsm=fsm,
                      action=action, seq=0, counter_value=counter_value, nextHeader=0)
    if action == actions["GENERATE_MULTIPLE_COUNTERS"]:
        pkt = pkt / FANCY_LENGTH(length=0)
    elif action == actions["MULTIPLE_COUNTERS"]:
        pkt = pkt / FANCY_LENGTH(length=mlength)
        if not multiple_counters or len(multiple_counters) < mlength:
            multiple_counters = range(mlength)
        for _counter in multiple_counters:
            pkt = pkt / FANCY_COUNTER(counter_value=_counter)
    elif action == actions["KEEP_ALIVE"] and count == 1:
        pkt[FANCY].nextHeader = IPV4
        pkt = pkt / IP(dst="11.0.2.2") / ("A" * 30)
    sendp(pkt, iface=iface, count=number)
    time.sleep(delay)
    return pkt


def send_stop_raw(iface, interval=None):
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

    finally:
        s.close()


def sender_machine():

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--iface', type=str, required=False, default="veth0")

    args = parser.parse_args()

    listener = Sniffer(args.iface, print_fancy_packet)
    listener.start()
    time.sleep(0.1)

    try:
        while True:
            data = raw_input("Insert packet to send (action ack count): ")
            if data:
                action, ack, count = data.split()
                action = actions[action]
                ack = int(ack)
                count = int(count)
            send_fancy_packet(args.iface, action, 0, ack, count)
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("[*] Stop sniffing")
        listener.join(2.0)

        if listener.isAlive():
            listener.socket.close()


def main():

    addr = "10.0.0.2"
    addr = socket.gethostbyname(addr)

    iface0 = "veth0"  # get_if()
    iface1 = "veth2"  # get_if()

    if len(sys.argv) > 2:
        iface0 = sys.argv[1]
        iface1 = sys.argv[2]

    listener = Sniffer(iface1)
    listener.start()
    time.sleep(0.1)

    try:
        while True:
            send_packet(iface0, addr)
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("[*] Stop sniffing")
        listener.join(2.0)

        if listener.isAlive():
            listener.socket.close()


if __name__ == '__main__':
    pass
    # main()
