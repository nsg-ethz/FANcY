/* State Machine Actions */
/* State machine action/tables */

action send_start() {
    hdr.fancy.setValid();
    hdr.fancy.id = meta.fancy_bridged.packet_id;
    hdr.fancy.nextHeader = hdr.ethernet.ether_type;
    hdr.ethernet.ether_type = ether_type_t.FANCY;
    hdr.fancy.action_value = START;
    hdr.fancy.count_flag = 0;
    hdr.fancy.ack = 0;
    hdr.fancy.fsm = 0;
    meta.fancy.counter_update_type_out = COUNTER_RESET;
}

action send_start_already_fancy() {
    hdr.fancy.action_value = START;
    hdr.fancy.count_flag = 0;
    hdr.fancy.ack = 0;
    hdr.fancy.fsm = 0;
    meta.fancy.counter_update_type_out = COUNTER_RESET;
}

action send_counter_ack() {
    hdr.fancy.action_value = COUNTER;
    hdr.fancy.count_flag = 0;
    hdr.fancy.ack = 1;
    hdr.fancy.fsm = 0;
    meta.fancy.counter_update_type_out = COUNTER_RESET;
}

action send_stop() {
    hdr.fancy.setValid();
    hdr.fancy.id = meta.fancy_bridged.packet_id;
    hdr.fancy.nextHeader = hdr.ethernet.ether_type;
    hdr.ethernet.ether_type = ether_type_t.FANCY;
    hdr.fancy.action_value = STOP;
    hdr.fancy.count_flag = 0;
    hdr.fancy.ack = 0;
    hdr.fancy.fsm = 0;
}

action send_stop_already_fancy() {
    hdr.fancy.action_value = STOP;
    hdr.fancy.count_flag = 0;
    hdr.fancy.ack = 0;
    hdr.fancy.fsm = 0;
}

action add_egress_fancy_header() {
    hdr.fancy.setValid();
    hdr.fancy.id = meta.fancy_bridged.packet_id;
    hdr.fancy.count_flag = 1;
    hdr.fancy.ack = 0;
    hdr.fancy.fsm = 0;
    hdr.fancy.nextHeader = hdr.ethernet.ether_type;
    hdr.fancy.action_value = 0;
    hdr.ethernet.ether_type = ether_type_t.FANCY;
    meta.fancy.counter_update_type_out = COUNTER_INCREASE;
}

action add_fancy_counter_header() {
    hdr.fancy.setValid();
    hdr.fancy.id = meta.fancy_bridged.packet_id;
    hdr.fancy.action_value = COUNTER;
    hdr.fancy.count_flag = 0;
    hdr.fancy.ack = 0;
    hdr.fancy.fsm = 1;
    hdr.fancy.counter_value = meta.fancy.local_counter_in;
    /* ethernet stuff */
    hdr.fancy.nextHeader = hdr.ethernet.ether_type;
    hdr.ethernet.ether_type = ether_type_t.FANCY;
}    

/* sets the fields properly*/
action add_fancy_pre_header()
{ 
    hdr.fancy_pre.setValid();
    hdr.ethernet.ether_type = ether_type_t.FANCY_PRE;
    hdr.fancy_pre.set_bloom = 1;
    hdr.fancy_pre.port = meta.fancy.original_port;
    hdr.fancy_pre.hash_0 = meta.fancy_bridged.packet_id;
}


/* Registers state */
/* Egress State Registers */

/* current register */
Register<bit<8>, reg_index_t>(NB_REGISTER_SIZE, 0) state_out;
RegisterAction<bit<8>, reg_index_t, state_t>(state_out)
read_update_state_out = {
    void apply(inout bit<8> value, out state_t rv) {
        
        /* if this is a control packet to update state */
        if (meta.fancy_state.control_type == STATE_UPDATE_EGRESS) {
            value = (bit<8>)meta.fancy_state.next_state;
        }
        /* Returns current state */
        rv = value;
    }
};

/* This is the counter used for state transition */
Register<bit<32>, reg_index_t>(NB_REGISTER_SIZE, 0) counters_out;
RegisterAction<bit<32>, reg_index_t, bit<32>>(counters_out)
update_counter_out = {
    void apply(inout bit<32> value, out bit<32> rv) {
        
        /* if this is a control packet to update state */
        if (meta.fancy_state.control_type == STATE_UPDATE_EGRESS) {
            value = 0;
        }
        else  {
            value = value + 1;
        }
        /* Returns current state */
        rv = value;
    }
};


/* h l
/* 0 0 -> 1 LOCK_NONE
/* 0 1 -> 2 LOCK_RELEASED
/* 1 0 -> 4 LOCK_OBTAINED
/* 1 1 -> 8 LOCK_ERROR
*/
/* ingress state machine state transition lock */
Register<bit<8>, reg_index_t>(NB_REGISTER_SIZE, 0) state_lock_out;
RegisterAction<bit<8>, reg_index_t, bit<4>>(state_lock_out)
read_update_state_lock_out = {
    void apply(inout bit<8> value, out bit<4> rv) {
        bool condition_lo = (meta.fancy_state.control_type == STATE_UPDATE_EGRESS);
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
Register<bit<32>, reg_index_t>(NB_REGISTER_SIZE, 0) pkt_counters_out;
RegisterAction<bit<32>, reg_index_t, bit<32>>(pkt_counters_out)
increase_pkt_counters_out = {
    void apply(inout bit<32> value, out bit<32> rv) {
        
        /* Returns counter before increasing (not sure why)*/
        rv = value;

        /* if this is a control packet to update state */
        if (meta.fancy.counter_update_type_out == COUNTER_INCREASE) {
            value = value + 1;
        }
        else if (meta.fancy.counter_update_type_out == COUNTER_RESET) {
            value = 0;
        }
    }
};

action set_egress_port_info (bit<16> address_offset, bit<2> egress_type) {
    /* Obtain addressing properties for this packet */
    meta.fancy.port_address_offset = address_offset;

    /* Get ingress type */
    meta.fancy.egress_type = egress_type;
}

table egress_port_info {
    key = {
        eg_intr_md.egress_port: exact;
    }
    actions = {
        set_egress_port_info;
        @defaultonly NoAction;
    }
    size = NUM_SWITCH_PORTS;
    default_action = NoAction();
}

action set_next_state_out (state_t next_state, bit<1> counter_type) {
    meta.fancy_state.next_state = next_state;
    meta.fancy_state.prev_state = meta.fancy.current_state;
    meta.fancy_state.state_change = 1;
    /* indicates that the transition was made by a counter hit */
    meta.fancy_state.state_change_counter = counter_type;
}

table table_next_state_out {
    key = {
        meta.fancy.current_state: exact;
        meta.fancy.current_counter: ternary;
        hdr.fancy.action_value: ternary;
        hdr.fancy.ack: ternary;
        hdr.fancy.fsm: ternary;
        hdr.fancy.isValid(): ternary;
    }
    actions = {
        set_next_state_out;
        @defaultonly NoAction;
    }
    default_action = NoAction();
}

table table_idle_to_start_ack_out {
    key = {
        hdr.fancy.isValid(): exact;
    }
    actions = {
        send_start;
        send_start_already_fancy;
        @defaultonly NoAction;
    }
    default_action =  NoAction();
    size =  2;
    const entries = {
        (false) : send_start();
        (true)  : send_start_already_fancy();
    }
}

table table_start_ack_to_start_ack_out {
    key = {
        hdr.fancy.isValid(): exact;
    }
    actions = {
        send_start;
        send_start_already_fancy;
        @defaultonly NoAction;
    }
    default_action =  NoAction();
    size =  2;
    const entries = {
        (false) : send_start();
        (true)  : send_start_already_fancy();
    }
}

table table_counting_to_wait_counter {
    key = {
        hdr.fancy.isValid(): exact;
    }
    actions = {
        send_stop;
        send_stop_already_fancy;
        @defaultonly NoAction;
    }
    default_action =  NoAction();
    size =  2;
    const entries = {
        (false) : send_stop();
        (true)  : send_stop_already_fancy();
    }
}

table table_wait_counter_to_start_ack {
    key = {
        hdr.fancy.isValid(): exact;
    }
    actions = {
        send_start;
        send_start_already_fancy;
        @defaultonly NoAction;
    }
    default_action =  NoAction();
    size =  2;
    const entries = {
        (false) : send_start();
        (true)  : send_start_already_fancy();
    }
}

table table_wait_counter_to_wait_counter {
    key = {
        hdr.fancy.isValid(): exact;
    }
    actions = {
        send_stop;
        send_stop_already_fancy;
        @defaultonly NoAction;
    }
    default_action =  NoAction();
    size =  2;
    const entries = {
        (false) : send_stop();
        (true)  : send_stop_already_fancy();
    }
}

action _clone_to_recirculation(MirrorId_t mirror_id){
    meta.fancy_bridged.is_internal = 1w1;
    meta.fancy_state.control_type = REROUTE_RECIRCULATE;
    meta.fancy.original_port = eg_intr_md.egress_port; // used for addressing after
    eg_dprsr_md.mirror_type = REROUTE_RECIRCULATE;
    meta.fancy.mirror_session = mirror_id;
    meta.fancy.mirror_header_type = HEADER_REROUTE_MIRRORING;
    // pipe 0 -> 100, pipe 1 -> 101
}

table clone_to_recirculation {
    actions = {
        _clone_to_recirculation;
    }
    key = {
        eg_intr_md.egress_port[8:7]: exact;
    }
    size = 4;
    default_action = _clone_to_recirculation(101); // pipe 0 -> 100, pipe 1 -> 101
}

action mirror_to_update() {
    meta.fancy_state.control_type = STATE_UPDATE_EGRESS;
    eg_dprsr_md.mirror_type = STATE_UPDATE_EGRESS;
    meta.fancy.mirror_session = (MirrorId_t)(eg_intr_md.egress_port) + 1;
    meta.fancy.mirror_header_type = HEADER_E2E_MIRRORING;
}