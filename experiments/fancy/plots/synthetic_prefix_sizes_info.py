# Synthetic prefixe sizes

def get_prefix_sizes_dedicated_counters():

    prefix_sizes = {}

    prefix_sizes[1] = [
        ("4Kbps", 1),
        ("8Kbps", 1),
        ("8Kbps", 2),
        ("25Kbps", 2),
        ("25Kbps", 5),
        ("50kbps", 5),
        ("50Kbps", 10),
        ("100Kbps", 10),
        ("100Kbps", 25),
        ("500Kbps", 25),
        ("500Kbps", 50),
        ("1Mbps", 50),
        ("1Mbps", 100),
        ("10Mbps", 100),
        ("10Mbps", 150),
        ("50Mbps", 150),
        ("100Mbps", 200),
        ("500Mbps", 250)]

    return prefix_sizes


def get_prefix_sizes_zooming():
    prefix_sizes = {}
    prefix_sizes[1] = [
        ("4Kbps", 1),
        ("8Kbps", 1),
        ("8Kbps", 2),
        ("25Kbps", 2),
        ("25Kbps", 5),
        ("50kbps", 5),
        ("50Kbps", 10),
        ("100Kbps", 10),
        ("100Kbps", 25),
        ("500Kbps", 25),
        ("500Kbps", 50),
        ("1Mbps", 50),
        ("1Mbps", 100),
        ("10Mbps", 100),
        ("10Mbps", 150),
        ("50Mbps", 150),
        ("100Mbps", 200),
        ("500Mbps", 250)]

    prefix_sizes[10] = [
        ("4Kbps", 1),
        ("8Kbps", 1),
        ("8Kbps", 2),
        ("25Kbps", 2),
        ("25Kbps", 5),
        ("50kbps", 5),
        ("50Kbps", 10),
        ("100Kbps", 10),
        ("100Kbps", 25),
        ("500Kbps", 25),
        ("500Kbps", 50),
        ("1Mbps", 50),
        ("1Mbps", 100),
        ("10Mbps", 100),
        ("10Mbps", 150),
        ("50Mbps", 150),
        ("100Mbps", 200),
        ("200Mbps", 200)]

    prefix_sizes[100] = [
        ("4Kbps", 1),
        ("8Kbps", 1),
        ("8Kbps", 2),
        ("25Kbps", 2),
        ("25Kbps", 5),
        ("50kbps", 5),
        ("50Kbps", 10),
        ("100Kbps", 10),
        ("100Kbps", 25),
        ("500Kbps", 25),
        ("500Kbps", 50),
        ("1Mbps", 50),
        ("1Mbps", 100),
        ("10Mbps", 100),
        ("10Mbps", 150),
        ("50Mbps", 150),
        ("100Mbps", 200),
        ("200Mbps", 200)]

    return prefix_sizes

# HELPERS


def transform_size_to_pkts_flows(prefix, pkt_size=500):
    """Helper function to transform size to pkts and flows

    Args:
        prefix (_type_): _description_
        pkt_size (int, optional): _description_. Defaults to 500.

    Returns:
        _type_: _description_
    """
    _bw_transform = {
        "gbps": 1000000000,
        "mbps": 1000000,
        "kbps": 1000,
    }

    bw, flows = prefix

    digits = ''.join(c for c in bw if c.isdigit())
    unit = ''.join(c for c in bw if not c.isdigit())

    # added this because by mistake one of the bandwidths is called kbps not Kbps
    unit = unit.lower()

    total_bits = int(digits) * _bw_transform[unit]

    total_pkts = total_bits / (8 * pkt_size)

    pkts_per_flow = total_pkts / int(flows)
    return int(pkts_per_flow), int(flows)


def format_prefix_sizes(prefix_sizes, bw=False):
    # check this properly
    prefix_sizes_formatted = {1: [], 10: [], 100: []}
    for num_prefixes, sizes in prefix_sizes.items():
        for prefix in sizes:
            if not bw:
                pkts, flows = transform_size_to_pkts_flows(prefix)
                prefix_sizes_formatted[num_prefixes].append(
                    "{0}/{1}".format(str(pkts), flows))
            else:
                prefix_sizes_formatted[num_prefixes].append(
                    "{0}/{1}".format(prefix[0], prefix[1]))

    return prefix_sizes_formatted
