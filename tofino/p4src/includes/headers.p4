/* PACKET HEADERS */

header_type ethernet_t {
    fields {
        dstAddr: 48;
        srcAddr   : 48;
        etherType : 16;
    }
}

header_type ipv4_t {
    fields {
        version        : 4;
        ihl            : 4;
        tos       : 8;
        totalLen       : 16;
        identification : 16;
        flags          : 3;
        fragOffset     : 13;
        ttl            : 8;
        protocol       : 8;
        hdrChecksum    : 16;
        srcAddr        : 32;
        dstAddr        : 32;
    }
}

// this is used to store the maximum counter diff
// and index as we are computing the maximum
// at the end we need to update it in the max register
// we only need to add/parse this header when we are doing the computation
// thus, we need some type of flag.

// 8 bytes
header_type fancy_pre_t {
    fields {
        _pad: 7;
        port: 9;
        set_bloom: 1; // will use to set the ingress rerouting thing
        pre_type: 7;
        max_index:  16; // we can have 256 counters, should be enough
        hash_0: 16; // will use as ID also for feeding info up in the normal fancy
        hash_1: 16;
        hash_2: 16; 
        max_counter_diff: 32; 
    }
}

/* 11 bytes */
header_type fancy_t {
    fields {
        id:       16;
        count_flag:     1;
        ack:       1;
        fsm:       1;
        action_value:  5;
        seq:            16;
        counter_value:    32;
        nextHeader:   16;
    }
}

header_type fancy_counters_length_t {
    fields {
        _length: 16; // we can have 256 counters, should be enough
    }
}

header_type fancy_counter_t {
    fields {
        counter_value: 32;
    }
}

header_type tcp_t {
    fields {
        srcPort: 16;
        dstPort: 16;
        seqNo      : 32;
        ackNo      : 32;
        dataOffset : 4;
        res        : 4;
        cwr        : 1;
        ece        : 1;
        urg        : 1;
        ack        : 1;
        psh        : 1;
        rst        : 1;
        syn        : 1;
        fin        : 1;
        window     : 16;
        checksum   : 16;
        urgentPtr  : 16;
    }
}

header_type udp_t {
    fields {
        srcPort  : 16;
        dstPort  : 16;
        hdrLen   : 16;
        checksum : 16;
    }
}

/* METADATA */

header_type fancy_meta_t {
fields
    {
      /* State machine Variables */
      current_counter: 32; // counter read at stage0
      current_state: 4; // state read from the first register
      prev_state  :  4; // state saved in a metadata in case we need it
      next_state  :  4; // state computed as next state to be updated
      state_change: 1;  // packet brings a state update 
      state_change_counter: 1; // if the state change was triggered by a counter threshold 
      control_type: 4; 
      lock_status: 4; // out state of the lock register: 1: LOCKED, 2: RELEASED, 4: OBTAINED, 8: ERORR/UNKOWN

      /* State machine addressing */
      packet_id: 16;
      port_address_offset: 16;
      dedicated_address: 16;

      /* reroute addresses */
      //output_port_address_offset: 16;
      reroute_address: 16;
      reroute: 1;

      /* Global variables */
      ingress_type: 2; /*swtich or host */
      egress_type: 2; /*swtich or host */
      entered_as_control: 1; /* if valid and action is set, if the packet entered with add_fancy_counter valid fancy header */

      /* I believe that usinf the FSM should be enough to know if the packet has
         to be processed at the egress, we use this to keep the same design we had in ns3
      */
      is_internal: 1; /* used for control packets generated in the ingress pipe */

      /* Counters */
      counter_update_type_in: 2;
      counter_update_type_out: 2;
      local_counter_out: 32;
      local_counter_in: 32;

      /* Extra metadata field to keep the original port when we clone to a different one */
      _pad: 7;
      original_port: 9;
    }
}

/* Debuggign switch stuff */
header_type debug_meta_t {
fields
    {
      drop_prefix_index: 16;
      drop_rate: 31;
      drop_packet: 1;
      drop_prefix_enabled: 1;
    }
}