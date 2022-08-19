/*************************************************************************
 ***********************  H E A D E R S  *********************************
 *************************************************************************/

/*  Define all the headers the program will recognize             */
/*  The actual sets of headers processed by each gress can differ */


// ETHERNET

typedef bit<48> mac_addr_t;

/* Protocols */

enum bit<16> ether_type_t {
    IPV4 = 0x0800,
    ARP  = 0x0806,
    TPID = 0x8100,
    IPV6 = 0x86DD,
    MPLS = 0x8847,
    FANCY = 0x0801,
    FANCY_PRE = 0x0802,
    LLDP = 0x88cc
}

/* Standard ethernet header */
header ethernet_h {
    mac_addr_t   dst_addr;
    mac_addr_t   src_addr;
    ether_type_t ether_type;
}

// IP

typedef bit<32> ipv4_addr_t;

enum bit<8> ip_protocol_t{
    UDP = 17, 
    TCP = 6
}

header ipv4_h {
    bit<4> version;
    bit<4> ihl;
    bit<8> tos;
    bit<16> total_len;
    bit<16> identification;
    bit<3> flags;
    bit<13> frag_offset;
    bit<8> ttl;
    ip_protocol_t protocol;
    bit<16> hdr_checksum;
    ipv4_addr_t src_addr;
    ipv4_addr_t dst_addr;
}

// TCP & UDP
header tcp_h {
    bit<16> src_port;
    bit<16> dst_port;
    bit<32> seq_no;
    bit<32> ack_no;
    bit<4> data_offset;
    bit<4> res;
    bit<8> flags;
    bit<16> window;
    bit<16> checksum;
    bit<16> urgent_ptr;
}

header udp_h {
    bit<16> src_port;
    bit<16> dst_port;
    bit<16> hdr_length;
    bit<16> checksum;
}


// FANCY PRE 
// this is used to store the maximum counter diff
// and index as we are computing the maximum
// at the end we need to update it in the max register
// we only need to add/parse this header when we are doing the computation
// thus, we need some type of flag.

header fancy_pre_h {
    @padding bit<7> _pad;
    bit<9> port; 
    bit<1> set_bloom; // will use to set the ingress rerouting thing
    bit<7> pre_type;
    bit<16> max_index; // we can have 256 counters, should be enough
    bit<16> hash_0; // will use as ID also for feeding info up in the normal fancy
    bit<16> hash_1;
    bit<16> hash_2;
    bit<32> max_counter_diff;
}   

header fancy_h {
    bit<16> id;
    bit<1> count_flag;
    bit<1> ack;
    bit<1> fsm;
    bit<5> action_value;
    bit<16> seq;
    bit<32> counter_value;
    ether_type_t nextHeader; // maybe can be removed with a look ahead?
}

header fancy_counters_length_h {
    bit<16> _length; // we can have 256 counters, should be enough
}

header fancy_counter_h {
    bit<32> counter_value;
}

typedef bit<8> state_t;

typedef bit<8> header_type_t;
#define INTERNAL_HEADER \
    header_type_t header_type

// HEADER TYPES
const header_type_t HEADER_NORMAL = 0;
// resubmit
const header_type_t HEADER_RESUBMIT = 8w1;
// mirrors
const header_type_t HEADER_I2E_MIRRORING = 8w2;
const header_type_t HEADER_E2E_MIRRORING = 8w3;
const header_type_t HEADER_REROUTE_MIRRORING = 8w4;

// Fancy headers for resub and e2e cloning
//@flexible
#ifdef MERGED
const bit<32> FANCY_RESUBMIT_SIZE = 32w48;
#else 
const bit<32> FANCY_RESUBMIT_SIZE = 32w40;
#endif
header fancy_resubmit_state_meta_h {
    //INTERNAL_HEADER; // we only have one resubmission and the meta flag, we can avoid this
    state_t prev_state;
    state_t next_state;
    @padding bit<2> _pad0;
    bit<1> state_change;
    bit<1> state_change_counter;
    bit<4> control_type;
    bit<16> packet_id; // this needs to be copied from the bridged one for mirroring, resub, etc
    #ifdef MERGED
    @padding bit<7> _pad1;
    bit<1> is_dedicated;
    #endif
}

// fields for i2e cloning
#ifdef MERGED
const bit<32> FANCY_INGRESS_MIRROR_SIZE = 32w80;
#else 
const bit<32> FANCY_INGRESS_MIRROR_SIZE = 32w72;
#endif
header fancy_ingress_mirror_h {
    INTERNAL_HEADER;
    bit<32> local_counter_in;
    bit<16> packet_id;
    @padding bit<7> _pad0;
    bit<1> is_internal;
    @padding bit<4> _pad1;
    bit<4> control_type;

    #ifdef MERGED
    @padding bit<7> _pad2;
    bit<1> is_dedicated;
    #endif
}

//@flexible
// e2e mirroring
#ifdef MERGED
const bit<32> FANCY_EGRESS_MIRROR_SIZE = 32w56;
#else 
const bit<32> FANCY_EGRESS_MIRROR_SIZE = 32w48;
#endif
header fancy_mirror_state_meta_h {
    INTERNAL_HEADER;
    state_t prev_state;
    state_t next_state;
    @padding bit<2> _pad0;
    bit<1> state_change;
    bit<1> state_change_counter;
    bit<4> control_type;
    bit<16> packet_id; // this needs to be copied from the bridged one for mirroring, resub, etc

    #ifdef MERGED
    @padding bit<7> _pad1;
    bit<1> is_dedicated;
    #endif
}

// fields for recirc cloning 
//@flexible
#ifdef MERGED
const bit<32> FANCY_REROUTE_MIRROR_SIZE = 32w64;
#else 
const bit<32> FANCY_REROUTE_MIRROR_SIZE = 32w56;
#endif
header fancy_reroute_mirror_h {
    INTERNAL_HEADER;
    bit<16> packet_id;

    @padding bit<7> _pad0;
    bit<1> is_internal;

    @padding bit<4> _pad1;
    bit<4> control_type;

    @padding bit<7> _pad2;
    bit<9> original_port;

    #ifdef MERGED
    @padding bit<7> _pad3;
    bit<1> is_dedicated;
    #endif
}

//@flexible
header fancy_bridged_meta_h {
    INTERNAL_HEADER;
    /* if valid and  action is set, if the packet entered with add_fancy_counter
    valid fancy header */
    @padding bit<7> _pad0;
    bit<1> entered_as_control; 
    @padding bit<7> _pad1;
    bit<1> is_internal; /* used for control packets generated in the ingress pipe */

    // state machine id
    bit<16> packet_id;

    // zooming stuff
    #ifdef MERGED

    // is the packet from a dedicated entry?
    @padding bit<7> _pad2;
    bit<1> is_dedicated;

    bit<16> hash_0;
    bit<16> hash_1;
    bit<16> hash_2;
    #endif
}

struct fancy_state_meta_h {
    state_t prev_state;
    state_t next_state;
    @padding bit<2> _pad1;
    bit<1> state_change;
    bit<1> state_change_counter;
    bit<4> control_type;
}

struct fancy_ingress_meta_h {
    // state counter
    bit<32> current_counter;  // Where we store the table counter
    /* reroute addresses */
    bit<16> reroute_address;
    state_t current_state; // state read from the first register
    bit<4> lock_status; // out state of the lock register: 1: LOCKED, 2: RELEASED, 4: OBTAINED, 8: ERORR/UNKOWN
    bit<2> ingress_type; /*swtich or host */
    bit<2> counter_update_type_in;
    bit<32> local_counter_in;
    // counter addresses 
    bit<16> port_address_offset;
    bit<16> dedicated_address;
    MirrorId_t mirror_session;
    header_type_t mirror_header_type;

    // zooming
    #ifdef MERGED
    bit<8> simple_address;
    bit<16> counter_address;
    #endif
}

struct fancy_egress_meta_h {
    // state counter
    bit<32> current_counter;  // Where we store the table counter
    state_t current_state; // state read from the first register
    bit<4> lock_status; // out state of the lock register: 1: LOCKED, 2: RELEASED, 4: OBTAINED, 8: ERORR/UNKOWN
    bit<2> egress_type; /*swtich or host */
    bit<2> counter_update_type_out;
    bit<32> local_counter_out;
    bit<32> local_counter_in;
    // counter addresses 
    bit<16> port_address_offset;
    bit<16> dedicated_address;
    MirrorId_t mirror_session;
    header_type_t mirror_header_type;
    @padding bit<7> _pad;
    /* Extra metadata field to keep the original port when we clone to a different one */
    bit<9> original_port;

    #ifdef MERGED
    // zooming
    bit<1> count_packet_flag;
    bit<16> max_0;
    bit<16> max_1;
    bit<8> zooming_stage;
    bit<8> simple_address;
    bit<16> counter_address;
    bit<32> local_counter_and_diff;  // saturating
    bit<32> counter_diff_excess;   // saturatning
    #endif

}