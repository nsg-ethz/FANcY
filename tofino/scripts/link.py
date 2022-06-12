#!/usr/bin/env python
import sys
import random
import time
from threading import Thread, Event, Lock
from scapy.all import *
from fancy_scapy import *
import sys


class Interface(Thread):
    def __init__(
            self, lock, intf1="veth0", intf2="veth2", connected=True,
            delays=[0, 0],
            loss=0, fail_ips=None):

        super(Interface, self).__init__()
        self.lock = lock
        self.intf1 = intf1
        self.intf2 = intf2
        self.connected = connected
        self.delays = delays
        self.daemon = True
        self.loss = loss
        self.drops = 0

        self.socket = None
        self.stop_sniffer = Event()
        self.packets_received_count = 0

        self.fail_ips = []
        if fail_ips:
            self.fail_ips = fail_ips

    def isNotOutgoing(self, pkt):
        return pkt[Ether].src != "ff:00:00:00:00:00"

    def run(self):

        self.socket = conf.L2listen(
            type=ETH_P_ALL,
            iface=self.intf1
        )

        # ugly trick
        if not self.intf2:
            self.isNotOutgoing = None

        sniff(opened_socket=self.socket, prn=self.send_packet_and_print,
              lfilter=self.isNotOutgoing, stop_filter=self.should_stop_sniffer)

    def join(self, timeout=None):
        self.stop_sniffer.set()
        super(Interface, self).join(timeout)

    def should_stop_sniffer(self, packet):
        return self.stop_sniffer.isSet()

    def drop(self, pkt):
        # only drop if fancy and count_flag
        # if (random.uniform(0,1) > 1-self.loss) and (FANCY in pkt and pkt[FANCY].count_flag==1):
        if (random.uniform(0, 1) > 1 - self.loss) and (IP in pkt):
            return True

    def send_packet_and_print(self, pkt):
        self.lock.acquire()
        if self.drop(pkt):
            self.drops += 1
            print(
                bcolors.WARNING + "Packet Dropped num {}".format(self.drops) +
                bcolors.ENDC)
        else:
            print_packet(pkt, True)
            #import ipdb; ipdb.set_trace()
            print("Packet number: {}, Packet Size: {}".format(
                self.packets_received_count, len(pkt)))
            self.packets_received_count += 1
            old_src = pkt[Ether].src
            pkt[Ether].src = 'ff:00:00:00:00:00'
            if self.connected:
                # check if the packet needs to be dropped
                if (((IP in pkt) and (not FANCY in pkt) or (FANCY in pkt and pkt[FANCY].action == actions["KEEP_ALIVE"])) and pkt[IP].dst in self.fail_ips):
                    print("drop")

                else:
                    time.sleep(random.uniform(self.delays[0], self.delays[1]))
                    print("Packet Sent: {}".format(get_now()))
                    # if old_src != "77:77:77:77:77:77":
                    sendp(pkt, iface=self.intf2, verbose=False)
                    # else:
                    #     print(bcolors.WARNING + "Packet Printed but not injected to the other side" + bcolors.ENDC)

            sys.stdout.flush()
        self.lock.release()


class Link():
    def __init__(
            self, intf1="veth0", intf2="veth2", connected=True, delays=[0, 0],
            loss=[0, 0],
            fail_ips=''):

        self.intf1 = intf1
        self.intf2 = intf2
        self.connected = connected
        self.loss = loss
        self.delays = delays
        self.lock = Lock()

        self.fail_ips = []
        if fail_ips:
            self.fail_ips = fail_ips.split(",")

    def run(self):
        if self.intf1:
            intferface1 = Interface(
                self.lock, self.intf1, self.intf2, self.connected, self.delays,
                self.loss[0],
                self.fail_ips)
            intferface1.start()

        if self.intf2:
            intferface2 = Interface(
                self.lock, self.intf2, self.intf1, self.connected, self.delays,
                self.loss[1],
                self.fail_ips)
            intferface2.start()

        time.sleep(0.1)

        print("Interface {}<->{} bridged".format(self.intf1, self.intf2))

        try:
            while True:
                time.sleep(100)
        except KeyboardInterrupt:
            print("[*] Stop sniffing")
            if self.intf1:
                intferface1.join(1)
            if self.intf2:
                intferface2.join(1)

            if self.intf1 and intferface1.isAlive():
                intferface1.socket.close()

            if self.intf2 and intferface2.isAlive():
                intferface2.socket.close()


if __name__ == '__main__':
    import sys
    connected = True

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--intf1', type=str, required=False, default="veth2")
    parser.add_argument('--intf2', type=str, required=False, default="veth4")
    parser.add_argument('--connected', type=bool,
                        required=False, default=False)
    parser.add_argument('--mindelay', type=float, required=False, default=0)
    parser.add_argument('--maxdelay', type=float, required=False, default=0)
    parser.add_argument('--loss1', type=float, required=False, default=0)
    parser.add_argument('--loss2', type=float, required=False, default=0)
    parser.add_argument('--fail_ips', type=str, required=False, default='')

    args = parser.parse_args()

    if not args.intf2:
        connected = False

    Link(
        args.intf1, args.intf2, args.connected,
        [args.mindelay, args.maxdelay],
        [args.loss1, args.loss2],
        args.fail_ips).run()
