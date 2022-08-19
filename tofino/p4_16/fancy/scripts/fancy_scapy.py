from scapy.all import *
import datetime

IPV4 = 0x0800
ARP = 0x0806
IPV6 = 0x86DD
_FANCY = 0x0801


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def get_now():
    currentDT = datetime.datetime.now()
    return currentDT.strftime("%H:%M:%S.%f")


# FANCY ACTIONS
actions = {"KEEP_ALIVE": 0, "START": 1, "STOP": 2, "COUNTER": 4,
           "MULTIPLE_COUNTERS": 16, "GENERATE_MULTIPLE_COUNTERS": 8}
reverse_actions = {y: x for x, y in actions.items()}


class FANCY(Packet):

    fields_desc = [BitField("id", 0, 16),
                   BitField("count_flag", 0, 1),
                   BitField("ack", 0, 1),
                   BitField("fsm", 0, 1),
                   BitField("action", 0, 5),
                   BitField("seq", 0, 16),
                   BitField("counter_value", 0, 32),
                   BitField("nextHeader", 0, 16)]


class FANCY_LENGTH(Packet):

    fields_desc = [BitField("length", 0, 16)]


class FANCY_COUNTER(Packet):

    fields_desc = [BitField("counter_value", 0, 32)]


bind_layers(Ether, FANCY, type=0x801)
bind_layers(FANCY, IP, nextHeader=0x800)
bind_layers(FANCY, FANCY, nextHeader=0x801)
bind_layers(FANCY, FANCY_LENGTH, action=actions["MULTIPLE_COUNTERS"])


def print_ip(pkt):
    ip = pkt.getlayer(IP)
    print("IP HEADER: SRC_IP={}, DST_IP={}, ID={}, TOS={}".format(
        ip.src, ip.dst, ip.id, ip.tos))


def print_fancy(pkt):
    fancy = pkt.getlayer(FANCY)
    if (reverse_actions[fancy.action] == "MULTIPLE_COUNTERS"):
        counters_length = pkt.getlayer(FANCY_LENGTH)
        print(
            "FANCY HEADER: ID={}, C/A/F={}{}{}, ACTION={}, COUNT={}, SEQ={}, NEXT=0x{:04x}".
            format(
                fancy.id, fancy.count_flag, fancy.ack, fancy.fsm,
                reverse_actions[fancy.action],
                fancy.counter_value, fancy.seq, fancy.nextHeader))

        payload = bytes(counters_length.payload)
        length = counters_length.length
        for i in range(length):
            print("counter {} {}".format(counters_length.length - i,
                  int.from_bytes(payload[i * 4:((i + 1) * 4)], "big")))

    elif (reverse_actions[fancy.action] == "COUNTER" and fancy.counter_value >= 0 and fancy.ack == 1):
        print(
            bcolors.WARNING +
            "FANCY HEADER: ID={}, C/A/F={}{}{}, ACTION={}, COUNT={}, SEQ={}, NEXT=0x{:04x}".
            format(
                fancy.id, fancy.count_flag, fancy.ack, fancy.fsm,
                reverse_actions[fancy.action],
                fancy.counter_value, fancy.seq, fancy.nextHeader) + bcolors.ENDC)
    else:
        print(
            "FANCY HEADER: ID={}, C/A/F={}{}{}, ACTION={}, COUNT={}, SEQ={}, NEXT=0x{:04x}".
            format(
                fancy.id, fancy.count_flag, fancy.ack, fancy.fsm,
                reverse_actions[fancy.action],
                fancy.counter_value, fancy.seq, fancy.nextHeader))

    if fancy.nextHeader == IPV4:
        print_ip(pkt)


def print_packet(pkt, print_all=False):

    ethernet = pkt.getlayer(Ether)
    direction = "x->y"
    if ethernet.src.endswith("01"):
        direction = "s1->s2"
    elif ethernet.src.endswith("02"):
        direction = "s2->s1"

    print("\nPacket Received: {}. ({})".format(get_now(), direction))

    print("ETHERNET HEADER: SRC={} DST={}".format(ethernet.src, ethernet.dst))

    if not print_all:
        if ethernet.type == 0x800 or ethernet.type == 0x86dd:
            return

    if ethernet.type == _FANCY:
        print_fancy(pkt)

    elif ethernet.type == IPV4:
        print_ip(pkt)
