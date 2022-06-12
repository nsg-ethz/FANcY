from fancy.python_simulations.crc import Crc
import socket
import struct
import pickle
import os
import time
import copy
import random

crc32_polinomials = [
    0x04C11DB7, 0xEDB88320, 0xDB710641, 0x82608EDB, 0x741B8CD7, 0xEB31D82E,
    0xD663B05, 0xBA0DC66B, 0x32583499, 0x992C1A4C, 0x32583499, 0x992C1A4C]


class IBF(object):

    def __init__(self, num_hashes=3):

        self.num_hashes = num_hashes

        # creates the 3 hashes that will use the p4 switch
        self.create_local_hashes()

    def create_local_hashes(self):
        self.hashes = []
        for i in range(self.num_hashes):
            self.hashes.append(
                Crc(32, crc32_polinomials[i], True, 0xffffffff, True, 0xffffffff))

    def generate_meter_difference(self, cells, hashes, errors):

        meter = {"counters": [0 for _ in range(cells)], "values": [
            0 for _ in range(cells)]}

        drop_packets = set()
        while len(drop_packets) != errors:
            drop_packets.add(random.randint(0, 2**32 - 1))

        drop_packets = list(drop_packets)

        for drop in drop_packets:
            for hash_index in range(hashes):
                hash_out = self.hashes[hash_index].bit_by_bit_fast(
                    struct.pack("I", drop)) % cells
                meter['counters'][hash_out] += 1
                meter['values'][hash_out] ^= drop

        return meter

    def compute_decoding_rate(self, register, num_hashes, num_drops):

        dropped_packets = set()
        meter = copy.deepcopy(register)
        while 1 in meter['counters']:
            i = meter['counters'].index(1)
            value = meter['values'][i]
            dropped_packets.add(value)

            # get the three indexes
            for hash_index in range(num_hashes):
                index = self.hashes[hash_index].bit_by_bit_fast(
                    struct.pack("I", value)) % len(
                    meter['counters'])
                meter['counters'][index] -= 1
                meter['values'][index] ^= value

        return len(dropped_packets) / num_drops

    def get_rate(self, num_cells, num_hashes, num_errors):

        meter = self.generate_meter_difference(
            num_cells, num_hashes, num_errors)
        print(self.compute_decoding_rate(meter, num_hashes, num_errors))


ibf = IBF(8)
