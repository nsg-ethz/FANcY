import struct
import random
from fancy.python_simulations.crc import Crc
import sys

crc32_polinomials = [
    0x04C11DB7, 0xEDB88320, 0xDB710641, 0x82608EDB, 0x741B8CD7, 0xEB31D82E,
    0xD663B05, 0xBA0DC66B, 0x32583499, 0x992C1A4C, 0x32583499, 0x992C1A4C]


def counter():
    i = 0

    def count():
        nonlocal i
        i += 1
        return i
    return count


def generate_prefixes(num, batch=10000):

    prefixes = set()

    while len(prefixes) < num:
        for _ in range(batch):
            prefixes.add(random.randint(0, 1000000000000))

    reminder = len(prefixes) - num
    for _ in range(reminder):
        prefixes.pop()

    return prefixes


def generate_paths(num_prefixes, failed_prefixes, width, levels, debug=False):

    prefixes = generate_prefixes(num_prefixes)

    #width = int(sys.argv[2])
    #levels = int(sys.argv[3])

    hashes = []
    for i in range(levels):
        hashes.append(
            Crc(32, crc32_polinomials[i], True, 0xffffffff, True, 0xffffffff))

    prefixes_paths = {}

    count = counter()

    r = 0
    count_failed_prefixes = 0
    for prefix in prefixes:
        r += 1
        s = ''
        for hash in hashes:

            hash_out = hash.bit_by_bit_fast(struct.pack("Q", prefix)) % width
            s += str(hash_out) + "-"

        fail_status = 0

        if count_failed_prefixes < failed_prefixes:
            count_failed_prefixes += 1
            fail_status = 1

        path = s[:-1]

        if path not in prefixes_paths:
            prefixes_paths[path] = [fail_status]
        else:
            prefixes_paths[path].append(fail_status)

        if debug:
            print(path)

        if r % 100000 == 0:
            print('{}'.format(count()))

    return prefixes_paths


def fast_generate_paths(
        num_prefixes, failed_prefixes, width, levels, debug=False):

    #width = int(sys.argv[2])
    #levels = int(sys.argv[3])

    prefixes_paths = {}

    count = counter()

    bucket_size = width**levels

    r = 0
    count_failed_prefixes = 0
    for _ in range(num_prefixes):
        r += 1

        path = random.randint(0, bucket_size)
        fail_status = 0

        if count_failed_prefixes < failed_prefixes:
            count_failed_prefixes += 1
            fail_status = 1

        if path not in prefixes_paths:
            prefixes_paths[path] = [fail_status]
        else:
            prefixes_paths[path].append(fail_status)

        if debug:
            print(path)

        if r % 100000 == 0:
            print('{}'.format(count()))

    return prefixes_paths


def find_collisions(prefixes_paths):
    """
    returns the numner of non failed prefixes that will be triggered
    Args:
        prefixes_paths:

    Returns:

    """

    count = 0
    for path, prefix_type in prefixes_paths.items():
        if 1 in prefix_type and 0 in prefix_type:
            count += prefix_type.count(0)
        elif 1 in prefix_type:
            print(prefix_type)

    return count


def count_start_with(prefixes, start_width):

    count = 0
    for prefix in prefixes:
        if prefix.startswith(start_width):
            print(prefix)
            count += 1

    return count


#index = hashes[0].bit_by_bit_fast((self.flow_to_bytestream(flow))) % mod
