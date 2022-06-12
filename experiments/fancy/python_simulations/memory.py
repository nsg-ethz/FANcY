LINK_FACTOR =2
MAX_ENTRY_BITS = 8
GLOBAL_TREE_COST = 128

def entry_based_memory(bit_per_entry, switch_ports, entries):

    """
    return the KB needed for this set up
    Args:
        bit_per_entry:
        switch_ports:
        entries:

    Returns:

    """

    return (bit_per_entry * entries * LINK_FACTOR * switch_ports)/float(8*1024)

def nodes_in_tree(depth, split):

    assert (depth > 1)
    assert (split > 0)

    if split == 1:
        return depth

    elif split > 1:
        return (split**depth -1) / (split -1)

def tree_based_memory(depth, split, bits_per_cell, node_width, switch_ports):

    assert (depth > 1)
    assert (split > 0)

    tree_nodes = nodes_in_tree(depth, split)
    node_cost =  (bits_per_cell) * node_width + (MAX_ENTRY_BITS * split * (depth - 1))
    tree_cost =  GLOBAL_TREE_COST + node_cost * tree_nodes * LINK_FACTOR

    total_cost = tree_cost * switch_ports
    print(node_width**depth/float(1000000))
    return total_cost/(8*1024)

