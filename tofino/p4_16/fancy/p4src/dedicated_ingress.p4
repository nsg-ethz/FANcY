    /* Rerouing register */
    Register<bit<1>, reg_index_t>(NB_REGISTER_SIZE, 0) reroute_register;

    RegisterAction<bit<1>, reg_index_t, bit<1>>(reroute_register)
    set_reroute_register = {
        void apply(inout bit<1> value, out bit<1> rv) {
            value = 1;
            rv = value;
        }
    };

    RegisterAction<bit<1>, reg_index_t, bit<1>>(reroute_register)
    get_reroute_register = {
        void apply(inout bit<1> value, out bit<1> rv) {
            rv = value;
        }
    };

    /* Ingress State Registers */

    /* current register */
    Register<bit<8>, reg_index_t>(NB_REGISTER_SIZE, 0) state_in;
    RegisterAction<bit<8>, reg_index_t, state_t>(state_in)
    read_update_state_in = {
        void apply(inout bit<8> value, out state_t rv) {
            
            /* if this is a control packet to update state */
            if (meta.fancy_state.control_type == STATE_UPDATE_INGRESS) {
                value = meta.fancy_state.next_state;
            }
            /* Returns current state */
            rv = value;
        }
    };

    /* This is the counter used for state transition */
    Register<bit<32>, reg_index_t>(NB_REGISTER_SIZE, 0) counters_in;
    RegisterAction<bit<32>, reg_index_t, bit<32>>(counters_in)
    update_counter_in = {
        void apply(inout bit<32> value, out bit<32> rv) {
            
            /* if this is a control packet to update state */
            if (meta.fancy_state.control_type == STATE_UPDATE_INGRESS) {
                value = 32w0;
            }
            else  {
                value = value + 32w1;
            }
            /* Returns current state */
            rv = value;
        }
    };

    /* ingress state machine state transition lock */
    Register<bit<8>, reg_index_t>(NB_REGISTER_SIZE, 0) state_lock_in;
    RegisterAction<bit<8>, reg_index_t, bit<4>>(state_lock_in)
    read_update_state_lock_in = {
        void apply(inout bit<8> value, out bit<4> rv) {
            bool condition_lo = (meta.fancy_state.control_type == STATE_UPDATE_INGRESS);
            /* register lo can be either 0 or 10 thus, if 1  state_change=1 */
            bool condition_hi = ((value + (bit<8>)meta.fancy_state.state_change) == 1);

            rv = this.predicate(condition_lo, condition_hi);
            // release lock
            if (condition_lo && !condition_hi) {
                value = 0;
            }
            // get lock
            else if (!condition_lo && condition_hi){
                value = LOCK_VALUE;
            }

        }
    };

    /* This is the counter used for packet counts*/
    Register<bit<32>, reg_index_t>(NB_REGISTER_SIZE, 0) pkt_counters_in;
    RegisterAction<bit<32>, reg_index_t, bit<32>>(pkt_counters_in)
    increase_pkt_counters_in = {
        void apply(inout bit<32> value, out bit<32> rv) {
            
            /* Returns counter before increasing (not sure why)*/
            rv = value;

            /* if this is a control packet to update state */
            if (meta.fancy.counter_update_type_in == COUNTER_INCREASE) {
                value = value + 1;
            }
            else if (meta.fancy.counter_update_type_in == COUNTER_RESET) {
                value = 0;
            }
        }
    };


/* ACTIONS */
action set_ingress_port_info (bit<16> address_offset, bit<2> ingress_type) {
    /* Obtain addressing properties for this packet */
    meta.fancy.port_address_offset = address_offset;

    /* Get ingress type */
    meta.fancy.ingress_type = ingress_type;
}

table ingress_port_info {
    key = {
        ig_intr_md.ingress_port: exact;
    }
    actions = {
        set_ingress_port_info;
        @defaultonly NoAction;
    }
    size = NUM_SWITCH_PORTS;
    default_action = NoAction();
}


action set_reroute_address (bit<16> address_offset) {
    meta.fancy.reroute_address = (address_offset + hdr.fancy_pre.hash_0);
}

table failed_port_to_reroute_address_set {
    key = {
        hdr.fancy_pre.port: exact;
    }
    actions = {
        set_reroute_address;
        @defaultonly NoAction;
    }
    size = NUM_SWITCH_PORTS;
    default_action = NoAction();
}

action read_reroute_address (bit<16> address_offset) {
    // TODO review if this is correct
    meta.fancy.reroute_address = (address_offset + meta.fancy_bridged.packet_id);
}

table read_reroute_register {
    key = {
        ig_tm_md.ucast_egress_port  : exact;
    }
    actions = {
        read_reroute_address;
        @defaultonly NoAction;
    }
    size = NUM_SWITCH_PORTS;
    default_action = NoAction();
}

table dedicated_reroute {
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

// State machine

action set_next_state_in (state_t next_state, bit<1> counter_type) {
    meta.fancy_state.next_state = next_state;
    meta.fancy_state.prev_state = meta.fancy.current_state;
    meta.fancy_state.state_change = 1;
    /* indicates that the transition was made by a counter hit */
    meta.fancy_state.state_change_counter = counter_type;
}

table table_next_state_in {
    key = {
        meta.fancy.current_state: exact;
        meta.fancy.current_counter: ternary;
        hdr.fancy.action_value: ternary;
        hdr.fancy.ack: ternary;
        hdr.fancy.isValid(): ternary;
    }
    actions = {
        set_next_state_in;
        @defaultonly NoAction;
    }
    default_action = NoAction();
    //const entries = {
    //    (8w10, 32w0 &&& 0, 5w0 &&& 0, 1w0 &&& 0, _): set_next_state_in(5, 1);
    //}
}

/* State machine actions */

/* send start ack  */
action send_start_ack () {
    hdr.fancy.action_value = START;
    hdr.fancy.count_flag = 0;
    hdr.fancy.ack = 1;
    hdr.fancy.fsm = 1;
    meta.fancy_bridged.is_internal = 1;
    ig_tm_md.ucast_egress_port = ig_intr_md.ingress_port;
}

action send_counter () {
    hdr.fancy.action_value = COUNTER;
    hdr.fancy.count_flag = 1w0;
    hdr.fancy.ack = 1w0;
    hdr.fancy.fsm = 1w1;
    hdr.fancy.counter_value = meta.fancy.local_counter_in;
    meta.fancy_bridged.is_internal = 1w1;
    ig_tm_md.ucast_egress_port = ig_intr_md.ingress_port;
}

/* Since sending this counter could be triggered by normal traffic we need
    to leave the packet unmodified at the ingress and then add stuff at the
    egress using a i2e clone 
*/
action send_counter_i2e() {
    meta.fancy_bridged.is_internal = 1;
    meta.fancy_state.control_type = INGRESS_SEND_COUNTER;
    meta.fancy.mirror_session = (MirrorId_t)ig_intr_md.ingress_port + 1;
    meta.fancy.mirror_header_type = HEADER_I2E_MIRRORING;
    ig_dprsr_md.mirror_type = INGRESS_SEND_COUNTER;
}