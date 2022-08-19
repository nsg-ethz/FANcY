    // Registers 
    // zooming stage
    Register<bit<8>, bit<8>>(NUM_SWITCH_PORTS, 0) zooming_stage;
    RegisterAction<bit<8>, bit<8>, bit<8>>(zooming_stage)
    read_update_zooming_stage = {
        void apply(inout bit<8> value, out bit<8> rv) {
            
            bool condition_lo = hdr.fancy_pre.pre_type >= UPDATE_OFFSET;  // the offset we set for this update
            bool condition_hi = value == MAX_ZOOM;

            rv = value;

            if (condition_lo && !condition_hi) {
                value = value +1;
            }
            else if (condition_lo && condition_hi) {
                value = 0;
            }

        }
    };

    /* Max indexes */
    Register<bit<16>, bit<8>>(NUM_SWITCH_PORTS, 0) max_0;
    RegisterAction<bit<16>, bit<8>, bit<16>>(max_0)
    register_read_update_max_0 = {
        void apply(inout bit<16> value, out bit<16> rv) {
            
            bool condition_lo = hdr.fancy_pre.pre_type == UPDATE_MAX_0; 

            // update
            if (condition_lo) {
                value = hdr.fancy_pre.max_index;
            }
            // read
            else if (!condition_lo) {
                value = value;
            }
            rv = value;
        }
    };

    Register<bit<16>, bit<8>>(NUM_SWITCH_PORTS, 0) max_1;
    RegisterAction<bit<16>, bit<8>, bit<16>>(max_1)
    register_read_update_max_1 = {
        void apply(inout bit<16> value, out bit<16> rv) {
            
            bool condition_lo = hdr.fancy_pre.pre_type == UPDATE_MAX_1; 

            // update
            if (condition_lo) {
                value = hdr.fancy_pre.max_index;
            }
            // read
            else if (!condition_lo) {
                value = value;
            }
            rv = value;
        }
    };

    /* State and counter */
    Register<bit<8>, bit<8>>(NUM_SWITCH_PORTS, 0) out_state;
    RegisterAction<bit<8>, bit<8>, bit<8>>(out_state)
    register_read_out_state = {
        void apply(inout bit<8> value, out bit<8> rv) {
            
            bool condition_lo = hdr.fancy.action_value == STOP; /* when we forward the STOP event to the other side */ 
            bool condition_hi = hdr.fancy_pre.pre_type >= UPDATE_OFFSET; /* last loop of counter exchange*/

            rv = value;

            if (condition_lo && !condition_hi) {
                value = SENDER_IDLE;
            }
            else if (condition_hi && !condition_lo) {
                value = SENDER_COUNTING;
            }
        }
    };

    Register<bit<32>, bit<10>>(ALL_PORTS_COUNTERS, 0) out_counters;
    RegisterAction<bit<32>, bit<10>, bit<32>>(out_counters)
    register_read_and_reset_counter = {
        void apply(inout bit<32> value, out bit<32> rv) {
            // reads
            rv = value;
            // resets
            value = 0;
        }
    };

    RegisterAction<bit<32>, bit<10>, bit<32>>(out_counters)
    add_to_counter = {
        void apply(inout bit<32> value) {
            value = value + 32w1;
        }
    };


    action set_egress_address_offsets_normal (bit<16> counter_offset, bit<8> simple_offset) {
        meta.fancy.counter_address = counter_offset;
        // were state is
        meta.fancy.simple_address = simple_offset;
    }

    // This could actually be optimized if we make the assumption that ingress and
    // egress port of this type of packets should be the same, if we need space, this can be done differently
    action set_egress_address_offsets_recirc (bit<16> counter_offset, bit<8> simple_offset) {
        meta.fancy.counter_address = counter_offset + hdr.fancy_counters_length._length;
        // were state is
        meta.fancy.simple_address = simple_offset;
    }

    table out_port_to_offsets {
        key = {
            hdr.fancy_pre.isValid(): exact;
            eg_intr_md.egress_port: ternary;
            hdr.fancy_pre.port: ternary;
        }
        actions = {
            set_egress_address_offsets_normal; 
            set_egress_address_offsets_recirc;
            @defaultonly NoAction;
        }
        size = NUM_SWITCH_PORTS;
        default_action = NoAction();
    }

    action update_read_zooming_stage()
    {
        meta.fancy.zooming_stage = read_update_zooming_stage.execute(meta.fancy.simple_address);
    }

    action read_update_max_0() {
        meta.fancy.max_0 = register_read_update_max_0.execute(meta.fancy.simple_address);
    }

    action read_update_max_1() {
        meta.fancy.max_1 = register_read_update_max_1.execute(meta.fancy.simple_address);
    }

    action read_out_state() {
        meta.fancy.current_state = register_read_out_state.execute(meta.fancy.simple_address);
    }

    action read_reset_counter() {
        meta.fancy.local_counter_and_diff = register_read_and_reset_counter.execute((bit<10>)meta.fancy.counter_address);
    }

    action build_hash_path() {
        hdr.fancy_pre.hash_0 = meta.fancy.max_0;
        hdr.fancy_pre.hash_1 = meta.fancy.max_1;
        // leaf index
        hdr.fancy_pre.hash_2 = hdr.fancy_counters_length._length; 

        // set bloom filter
        hdr.fancy_pre.set_bloom = 1;
    }

    action _set_fancy_pre_type(bit<7> _type) {
        hdr.fancy_pre.pre_type = _type;
    }

    table set_fancy_pre_type_to_update {
        key = {
            hdr.fancy_counters_length._length: exact;
            meta.fancy.zooming_stage: exact;
        }
        actions = {
            _set_fancy_pre_type;
            @defaultonly NoAction;
        }
        size = 8;
        default_action = NoAction();
    }

    action subtract_differences() {
        meta.fancy.counter_diff_excess = hdr.fancy_pre.max_counter_diff |-| meta.fancy.local_counter_and_diff;
    }

    action subtract_counters() {
        meta.fancy.local_counter_and_diff = meta.fancy.local_counter_and_diff |-| hdr.fancy_counter.counter_value;
        hdr.fancy_counter.setInvalid();
    }

    action remove_fancy_header() {
        hdr.ethernet.ether_type = hdr.fancy.nextHeader;
        hdr.fancy.setInvalid();
    }

    action add_fancy_counting_header() {
        hdr.fancy.setValid();
        hdr.fancy.id = ENTRY_ZOOM_ID;
        hdr.fancy.count_flag = 1;
        hdr.fancy.ack = 0;
        hdr.fancy.fsm = 0;
        hdr.fancy.nextHeader = hdr.ethernet.ether_type;
        hdr.fancy.action_value = 0;
        hdr.ethernet.ether_type = ether_type_t.FANCY;
    }

    action set_zoom_address_0() {
        // address carrier
        hdr.fancy.seq = meta.fancy_bridged.hash_0;
        meta.fancy.counter_address = meta.fancy.counter_address + meta.fancy_bridged.hash_0;
        meta.fancy.count_packet_flag = 1;
    }

    action set_zoom_address_1() {
        // address carrier
        hdr.fancy.seq = meta.fancy_bridged.hash_1;
        meta.fancy.counter_address = meta.fancy.counter_address + meta.fancy_bridged.hash_1;
        meta.fancy.count_packet_flag = 1;
    }

    action set_zoom_address_2() {
        // address carrier
        hdr.fancy.seq = meta.fancy_bridged.hash_2;
        meta.fancy.counter_address = meta.fancy.counter_address + meta.fancy_bridged.hash_2;
        meta.fancy.count_packet_flag = 1;
    }

    action _add_to_counter() {
        add_to_counter.execute((bit<10>)meta.fancy.counter_address);
    }