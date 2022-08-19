/* Registers */

/* Bloom filters */
Register<bit<1>, bloom_index_t>(BLOOM_FILTER_SIZE, 0) bloom_filter_1;
RegisterAction<bit<1>, bloom_index_t, bit<1>>(bloom_filter_1)
set_bf_1 = {
    void apply(inout bit<1> value, out bit<1> rv) {
        value = 1;
        rv = value;
    }
};
RegisterAction<bit<1>, bloom_index_t, bit<1>>(bloom_filter_1)
read_bf_1 = {
    void apply(inout bit<1> value, out bit<1> rv) {
        //value = value;
        rv = value;
    }
};

Register<bit<1>, bloom_index_t>(BLOOM_FILTER_SIZE, 0) bloom_filter_2;
RegisterAction<bit<1>, bloom_index_t, bit<1>>(bloom_filter_2)
set_bf_2 = {
    void apply(inout bit<1> value, out bit<1> rv) {
        value = 1;
        rv = value;
    }
};
RegisterAction<bit<1>, bloom_index_t, bit<1>>(bloom_filter_2)
read_bf_2 = {
    void apply(inout bit<1> value, out bit<1> rv) {
        //value = value;
        rv = value;
    }
};


/* Zooming State and counter */
Register<bit<8>, bit<8>>(NUM_SWITCH_PORTS, 0) in_state;
RegisterAction<bit<8>, bit<8>, bit<8>>(in_state)
read_in_state = {
    void apply(inout bit<8> value, out bit<8> rv) {
        //value = value;
        rv = value;
    }
};

Register<bit<32>, bit<10>>(ALL_PORTS_COUNTERS, 0) in_counters;
RegisterAction<bit<32>, bit<10>, bit<32>>(in_counters)
read_in_counter = {
    void apply(inout bit<32> value, out bit<32> rv) {
        //value = value;
        rv = value;
        // and resets... (think a better way)
        value = 0;
    }
};
RegisterAction<bit<32>, bit<10>, bit<32>>(in_counters)
increase_in_counter = {
    void apply(inout bit<32> value, out bit<32> rv) {
        value = value |+| 32w1;
        rv = value;
    }
};


/* ACTIONS */

table zooming_reroute {
    key = {
        ig_tm_md.ucast_egress_port  : exact;
    }
    actions = {
        set_port;
        @defaultonly NoAction;
    }
    size = NUM_SWITCH_PORTS;
    default_action = NoAction();
}


action set_ingress_address_offsets_normal (bit<16> counter_offset, bit<8> simple_offset) {
    meta.fancy.counter_address = counter_offset + hdr.fancy.seq;
    // were state is
    meta.fancy.simple_address = simple_offset;
}

action set_ingress_address_offsets_recirc (bit<16> counter_offset, bit<8> simple_offset) {
    meta.fancy.counter_address = counter_offset + hdr.fancy_counters_length._length;
    // were state is
    meta.fancy.simple_address = simple_offset;
}

table in_port_to_offsets {
    key = {
        hdr.fancy_pre.isValid(): exact;
        ig_intr_md.ingress_port: ternary;
        hdr.fancy_pre.port: ternary;
    }
    actions = {
        set_ingress_address_offsets_normal; 
        set_ingress_address_offsets_recirc;
        @defaultonly NoAction;
    }
    size = NUM_SWITCH_PORTS;
    default_action = NoAction();
}

// Zooming hashes

// crc_32
CRCPolynomial<bit<16>>(16w4129, false, false, true, 16w65535, 16w0) h0;
Hash<hash_size_t>(HashAlgorithm_t.CUSTOM, h0) hash_0;
// crc_32c
CRCPolynomial<bit<16>>(16w1417, false, false, true, 16w1, 16w1) h1;
Hash<hash_size_t>(HashAlgorithm_t.CUSTOM, h1) hash_1;
// crc_32d
CRCPolynomial<bit<16>>(16w15717, true, false, true, 16w0, 16w65535) h2;
Hash<hash_size_t>(HashAlgorithm_t.CUSTOM, h2) hash_2;

action compute_packet_hashes() {
    meta.fancy_bridged.hash_0 = (bit<16>)hash_0.get({hdr.ipv4.dst_addr});
    meta.fancy_bridged.hash_1 = (bit<16>)hash_1.get({hdr.ipv4.dst_addr});
    //meta.fancy_bridged.hash_2 = hash_2.get({hdr.ipv4.dst_addr});
}
action compute_packet_hashes1() {
    meta.fancy_bridged.hash_2 = (bit<16>)hash_2.get({hdr.ipv4.dst_addr});
}

//CRCPolynomial<bit<33>>(0x104C11DB7, true, false, false, 0x00000000, 0xFFFFFFFF) crc_32;
CRCPolynomial<bit<32>>(32w79764919, true, false, true, 32w4294967295, 32w4294967295) crc_32;

//// crc_32c
//CRCPolynomial<bit<33>>(0x11EDC6F41, true, false, false, 0x00000000, 0xFFFFFFFF) crc_32c;
CRCPolynomial<bit<32>>(32w79764919, true, false, true, 32w4294967295, 32w4294967295) crc_32c;

    // hashes for the path
Hash<bit<16>>(HashAlgorithm_t.CUSTOM, crc_32) ing_path_hash_0;
Hash<bit<16>>(HashAlgorithm_t.CUSTOM, crc_32c) ing_path_hash_1;

Hash<bit<16>>(HashAlgorithm_t.CUSTOM, crc_32) egr_path_hash_0;
Hash<bit<16>>(HashAlgorithm_t.CUSTOM, crc_32c) egr_path_hash_1;

action set_generating_multiple_counters()
{
    // pre header
    hdr.fancy_pre.setValid();
    hdr.fancy_pre.pre_type =  0;
    hdr.fancy_pre.port = ig_intr_md.ingress_port;
    hdr.ethernet.ether_type = ether_type_t.FANCY_PRE;

    // Add fancy counters header 
    hdr.fancy_counters_length.setValid();
    hdr.fancy.action_value = GENERATING_MULTIPLE_COUNTERS;
    hdr.fancy_counters_length._length = 0;
}

action add_fancy_counter() {
    hdr.fancy_counter.setValid();
    hdr.fancy_counters_length._length = hdr.fancy_counters_length._length + 1;
    hdr.fancy_counter.counter_value = read_in_counter.execute((bit<10>)meta.fancy.counter_address);
}

action return_counter()
{
    // sets initial port
    ig_tm_md.ucast_egress_port = hdr.fancy_pre.port;
    hdr.ethernet.ether_type = ether_type_t.FANCY;
    hdr.fancy.action_value = MULTIPLE_COUNTERS;
    hdr.fancy.id = ENTRY_ZOOM_ID;

    // set fsm
    hdr.fancy.fsm = 1;

    // remove pre header since its internally used for recirculation
    hdr.fancy_pre.setInvalid();

    //bypass egress
    ig_tm_md.bypass_egress = 1;
    // remove the header since we do not parse/deparse at the egress!!
    meta.fancy_bridged.setInvalid();
}

action _set_computing_multiple_counters()
{
    // pre header
    hdr.fancy_pre.setValid();
    hdr.fancy_pre.set_bloom = 0;
    hdr.fancy_pre.pre_type = 0;
    hdr.fancy_pre.port = ig_intr_md.ingress_port;
    hdr.ethernet.ether_type = ether_type_t.FANCY_PRE;
    hdr.fancy_pre.max_index = 0;
    hdr.fancy_pre.max_counter_diff = 0;
}