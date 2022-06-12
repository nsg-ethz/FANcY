from tabulate import tabulate

# Features

# bw in bit/s
bandwidth = [10e9, 40e9, 100e9]
bandwidth = [100e9]

# avg pkt size in bytes
avg_pkt_size = [100, 300, 500, 1000, 1500]

# response size in bytes
response_size = [4, 14, 40, 64, 128]

ack_factor = [1, 2, 5, 10, 100, 1000]


headers = ['bw', 'avg_pkt_size', 'res_size',
           'ack_mult', 'bw_overhead', 'packet_overhead']

results = []

for bw in bandwidth:
    for avg_s in avg_pkt_size:
        for res_size in response_size:
            for ack_f in ack_factor:

                packets = (bw / (avg_s * 8))
                bw_overhead = packets * (res_size * 8) / ack_f
                packet_ovehead = packets / ack_f

                #

                results.append([bw / 1e9, avg_s, res_size, ack_f,
                               bw_overhead / 1e9, packet_ovehead])

if __name__ == "__main__":
    print(
        tabulate(
            results, headers=headers, tablefmt='fancy_grid',
            numalign='right'))
