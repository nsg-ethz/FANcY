#include <core.p4>

#if __TARGET_TOFINO__ == 2
    #include <t2na.p4>
#else
    #include <tna.p4>
#endif

#if __TARGET_TOFINO__ != 1
    #define RECIRCULATION_PORT 6
    #define CPU_ETH_PORT(n) (2 + (n) & 0x3)
#else
    #define RECIRCULATION_PORT 68
    #define CPU_ETH_PORT(n) (64 + (n) & 0x3)
#endif

//#define HARDWARE
#define REROUTE
#define MERGED

#include "../includes/constants.p4"
#include "../includes/headers.p4"



/*************************************************************************
 **************  I N G R E S S   P R O C E S S I N G   *******************
 *************************************************************************/

/***********************  H E A D E R S  ************************/

struct my_ingress_headers_t {
    ethernet_h ethernet;
    fancy_pre_h fancy_pre; // this is kind of a bridge/recirc meta
    fancy_h fancy;
    fancy_counters_length_h fancy_counters_length;
    fancy_counter_h fancy_counter;
    ipv4_h ipv4;
}


/******  G L O B A L   I N G R E S S   M E T A D A T A  *********/
struct my_ingress_metadata_t {
    fancy_bridged_meta_h fancy_bridged;
    fancy_state_meta_h fancy_state;
    fancy_ingress_meta_h fancy;
}


/***********************  P A R S E R  **************************/
parser IngressParser(packet_in        pkt,
    /* User */
    out my_ingress_headers_t          hdr,
    out my_ingress_metadata_t         meta,
    /* Intrinsic */
    out ingress_intrinsic_metadata_t  ig_intr_md)
{

    state start {
        pkt.extract(ig_intr_md);

        // all meta to 0
        //meta.fancy_state.prev_state = 0;
        meta.fancy_state.prev_state = 0;
        meta.fancy_state.control_type = 0;
        meta.fancy_state.next_state = 0;
        meta.fancy_state.state_change = 0;
        meta.fancy_state.state_change_counter = 0;

        meta.fancy = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0}; 

        // bridged header
        meta.fancy_bridged.setValid();
        meta.fancy_bridged.header_type = HEADER_NORMAL;

        transition select(ig_intr_md.resubmit_flag) {
            1: parse_resubmit;
            0: parse_ethernet;
        }
    }

    state parse_resubmit {
        fancy_resubmit_state_meta_h rh;
        rh = pkt.lookahead<fancy_resubmit_state_meta_h>();
        // copy values to general header
        meta.fancy_bridged.setValid();

        meta.fancy_bridged.packet_id = rh.packet_id;
        meta.fancy_bridged.is_dedicated = rh.is_dedicated;
        meta.fancy_state.prev_state = rh.prev_state;
        meta.fancy_state.next_state = rh.next_state;
        meta.fancy_state.state_change = rh.state_change;
        meta.fancy_state.state_change_counter = rh.state_change_counter;
        meta.fancy_state.control_type = rh.control_type;

        transition parse_ethernet;

    }
    
    state parse_ethernet {
        // parse porn metadata
        pkt.advance(PORT_METADATA_SIZE);
        pkt.extract(hdr.ethernet);
        transition select(hdr.ethernet.ether_type) {
            ether_type_t.IPV4 : parse_ipv4;
            ether_type_t.FANCY: parse_fancy;
            ether_type_t.FANCY_PRE: parse_fancy_pre;
            default : accept;
        }
    }

    state parse_fancy_pre {
        pkt.extract(hdr.fancy_pre);
        transition parse_fancy;
    }

    state parse_fancy {
        pkt.extract(hdr.fancy);
        transition select(hdr.fancy.nextHeader, hdr.fancy.action_value)
        {
            (ether_type_t.IPV4, _): parse_ipv4; 
            (_, MULTIPLE_COUNTERS_PARSER): parse_fancy_counters_length_and_counter;
            (_, GENERATING_MULTIPLE_COUNTERS_PARSER): parse_fancy_counters_length;
            default: accept;
        }
    }

    state parse_fancy_counters_length_and_counter{
        pkt.extract(hdr.fancy_counters_length);
        pkt.extract(hdr.fancy_counter);
        transition accept;
    }

    state parse_fancy_counters_length {
        pkt.extract(hdr.fancy_counters_length);
        transition accept;
    }

    state parse_ipv4 {
        pkt.extract(hdr.ipv4);
        transition accept;
    }


}

    /***************** M A T C H - A C T I O N  *********************/

control Ingress(
    /* User */
    inout my_ingress_headers_t                       hdr,
    inout my_ingress_metadata_t                      meta,
    /* Intrinsic */
    in    ingress_intrinsic_metadata_t               ig_intr_md,
    in    ingress_intrinsic_metadata_from_parser_t   ig_prsr_md,
    inout ingress_intrinsic_metadata_for_deparser_t  ig_dprsr_md,
    inout ingress_intrinsic_metadata_for_tm_t        ig_tm_md)
{  

    /* Generic Actions */

    /* drop 3-bit field:
    [2]-> disable mirroring
    [1]-> disable copy_to_cpu
    [0]-> disable unicast, multicast or resubmit
    */

    action drop_exit_ingress () {
        ig_dprsr_md.drop_ctl = 1;
        exit;
    }

    action drop_ingress () {
        ig_dprsr_md.drop_ctl = 1;
    }

    action strong_drop_ingress () {
        ig_dprsr_md.drop_ctl = 7;
    }

    action set_port(PortId_t port) {
        ig_tm_md.ucast_egress_port = port;
    }

    table forward {
        key = {
            ig_intr_md.ingress_port: exact;
        }
        actions = {
            set_port; 
            @defaultonly NoAction;
        }
        size = NUM_SWITCH_PORTS;
        default_action = NoAction();
    }

    /* we set the dedicated entry id */
    action set_packet_id_zooming()
    {
        meta.fancy_bridged.packet_id = ENTRY_ZOOM_ID;
        // NEW
        meta.fancy_bridged.is_dedicated = 0;
    }

    action set_packet_id_dedicated(bit<16> packet_id)
    {
        meta.fancy_bridged.packet_id = packet_id;
        // NEW
        meta.fancy_bridged.is_dedicated = 1;
    }

    table packet_to_id {
        key = {
            hdr.ipv4.dst_addr: exact;
        }
        actions = {
            set_packet_id_dedicated;
            @defaultonly set_packet_id_zooming;
        }
        default_action = set_packet_id_zooming ();
        size = NUM_DEDICATED_ENTRIES;
    }

    action set_dedicated_addres() {
        // get dedicated address
        meta.fancy.dedicated_address = meta.fancy.port_address_offset + meta.fancy_bridged.packet_id;
    }

    action same_pipe_recirculate() {
        ig_tm_md.ucast_egress_port[6:0] = RECIRCULATION_PORT;
        ig_tm_md.ucast_egress_port[8:7] = ig_intr_md.ingress_port[8:7];
    }

    #include "dedicated_ingress.p4"
    #include "zooming_ingress.p4"


    apply {

        // Drop all LLDP packets. 
        if (hdr.ethernet.isValid() && hdr.ethernet.ether_type == ether_type_t.LLDP) {
            drop_exit_ingress();
        }

        // Zooming: Compute hashes
        /* Compute the three hashes always */
        compute_packet_hashes();
        compute_packet_hashes1();

        /* Decide if this packet is not a control packet */
        /* When it arrives */
        /* this also affects resubmissions */        
        if (hdr.fancy.isValid() && hdr.fancy.action_value != KEEP_ALIVE) {
            // Keep alive packets can be counting packets, thus they do not
            // count as control.
            meta.fancy_bridged.entered_as_control = 1;
        }

        /* Normal Forwarding Table */
        forward.apply();

        /* Gather Ingress Port Info  */
        ingress_port_info.apply();

        /* Get address offsets */
        /* Sets the offset depending if the packet has Fancy or Fancy pre */
        // NEW ZOOMING
        in_port_to_offsets.apply();

        /* Deciding if its a dedicated entry or not */
        if (hdr.fancy.isValid()) {
            // zooming
            if (hdr.fancy.id == ENTRY_ZOOM_ID) {
                meta.fancy_bridged.is_dedicated = 0;
            }
            // dedicated
            else {
                meta.fancy_bridged.is_dedicated = 1;
                // get it from the header, just in case for the egress part.
                meta.fancy_bridged.packet_id = hdr.fancy.id;
            }
        }
        else {
            /* Get packet ID */
            /* If its a dedicated counter entry we get a number from 0 to 510,
            otherwise 511 for the tree? */
            packet_to_id.apply();
        }

        // get main dedicated address
        set_dedicated_addres();

        // Begining of STAGE 1/2

        /* Filter control pakcets that enter from a host port */
        // TODO think how to block things here but not STOPS
        #ifdef HARDWARE
        if (!(ig_intr_md.ingress_port == PORT4_S || ig_intr_md.ingress_port[6:0] == RECIRCULATION_PORT) && 
            meta.fancy.ingress_type == HOST && meta.fancy_bridged.entered_as_control == 1)
        {
            drop_exit_ingress();
        }
        #else
        if (!(ig_intr_md.ingress_port == PORT4_M || ig_intr_md.ingress_port[6:0] == RECIRCULATION_PORT) && 
            meta.fancy.ingress_type == HOST && meta.fancy_bridged.entered_as_control == 1)
        {
            drop_exit_ingress();
        }
        #endif

        /* Reroute Logic */
        /* Set Reroute Bit */
        if (meta.fancy_bridged.is_dedicated == 1) {
           if (hdr.fancy_pre.isValid() && hdr.fancy_pre.set_bloom == 1) {
                /* sets the reroute bit for this entry and port  */
                failed_port_to_reroute_address_set.apply();

                /* set bit */
                set_reroute_register.execute(meta.fancy.reroute_address);
                /* finish an drop this packetr */
                drop_exit_ingress();

            }
            /* Reroute normal traffic */
            else if (hdr.ipv4.isValid()) { //&& meta.fancy_bridged.packet_id != ENTRY_ZOOM_ID) {
                
                /* Read reroute bit  */
                read_reroute_register.apply();

                /* read bit */
                bit<1> _reroute;
                _reroute = get_reroute_register.execute(meta.fancy.reroute_address);

                if (_reroute == 1) {
                    dedicated_reroute.apply();
                }
            }
        }
        else {
            // REROUTING LOGIC, not sure it should be tight to any state probably not.
            if (hdr.fancy_pre.isValid() && hdr.fancy_pre.set_bloom == 1) {
                // clear flag for next packets
                hdr.fancy_pre.set_bloom = 0;
                // sets bloom filter
                set_bf_1.execute(egr_path_hash_0.get({hdr.fancy_pre.hash_0, hdr.fancy_pre.hash_1, hdr.fancy_pre.hash_2}));
                set_bf_2.execute(egr_path_hash_1.get({hdr.fancy_pre.hash_0, hdr.fancy_pre.hash_1, hdr.fancy_pre.hash_2}));
            }
            else if (hdr.ipv4.isValid())
            {
                // Read blom filters
                bit<1> bf_1;
                bit<1> bf_2;
                bf_1 = read_bf_1.execute(ing_path_hash_0.get({meta.fancy_bridged.hash_0, meta.fancy_bridged.hash_1, meta.fancy_bridged.hash_2}));
                bf_2 = read_bf_2.execute(ing_path_hash_1.get({meta.fancy_bridged.hash_0, meta.fancy_bridged.hash_1, meta.fancy_bridged.hash_2}));

                if (bf_1 == 1 && bf_2 == 1){
                    zooming_reroute.apply();
                }
             }            
        }

        // dedicated
        if (meta.fancy_bridged.is_dedicated == 1) {
            /* State Machine */
            // If Packet comes from an egress fancy switch
            if (meta.fancy.ingress_type == FANCY_SWITCH)
            {
                /* For now we wont use them to count, it could get messy if we do */
                /* this is directly sent to the egress */
                if (meta.fancy_bridged.entered_as_control == 1 && hdr.fancy.fsm == 1) {
                    // ingress port to egress port for control packet from another ingress
                    ig_tm_md.ucast_egress_port = ig_intr_md.ingress_port;
                    // exit execution
                    exit;
                }

                /* STATE MACHINE */            
                /* Read and update state */
                meta.fancy.current_state = read_update_state_in.execute(meta.fancy.dedicated_address);
                meta.fancy.current_counter = update_counter_in.execute(meta.fancy.dedicated_address);

                /* Ingress Count packets: read & update & reset */
                /*************************************************************/
                if (meta.fancy.current_state == RECEIVER_COUNTING && hdr.fancy.count_flag == 1) {
                    /* set flag to increase */
                    meta.fancy.counter_update_type_in = COUNTER_INCREASE;
                }
                /* Maybe: also check if the start matches in the state transition
                table. This could be an attack vector. This can be used to reset the
                counter all the time right?*/
                else if (hdr.fancy.action_value == START) {
                    /* set flag to reset */ 
                    meta.fancy.counter_update_type_in = COUNTER_RESET;
                }

                /* if no flag set we should just read it*/
                /* The flags are set in the two previous conditions */
                meta.fancy.local_counter_in = increase_pkt_counters_in.execute(meta.fancy.dedicated_address);
                /*************************************************************/


                /* Compute next state */
                /* If control type is not 0 we dont check this */
                if (meta.fancy_state.control_type == 0) {
                    /* If its a control packet and did not hit the table we drop it  inmediately */
                    /* control packets that do not hit, they got lost maybe? */
                    if (table_next_state_in.apply().miss) {
                        if (meta.fancy_bridged.entered_as_control == 1) {
                            drop_exit_ingress();
                        }                    
                    }
                }

                /* Lock state or check if state is locked */
                meta.fancy.lock_status = read_update_state_lock_in.execute(meta.fancy.dedicated_address);

                /* STATE MACHINE LOGIC */
                /* If state was locked now, we resubmit */
                if (meta.fancy.lock_status == LOCK_OBTAINED){
                    /* Enable packet resubmit */
                    meta.fancy_state.control_type = STATE_UPDATE_INGRESS;
                    ig_dprsr_md.resubmit_type = STATE_UPDATE_INGRESS;
                }   
                else if (meta.fancy.lock_status == LOCK_RELEASED) {
                    /* State transitions */
                    
                    /* From idle to counting */
                    if (meta.fancy_state.prev_state == RECEIVER_IDLE && meta.fancy_state.next_state == RECEIVER_COUNTING) {
                        /*  1. Reset counting counter
                            2. Set received SEQ number */
                        send_start_ack();
                    }
                    else if (meta.fancy_state.prev_state == RECEIVER_COUNTING && meta.fancy_state.next_state == RECEIVER_COUNTING) {
                        /*  1. Reset counting counter
                            2. Set received SEQ number */
                        send_start_ack();
                    }

                    //else if (meta.fancy_state.prev_state == RECEIVER_COUNTING and meta.fancy_state.next_state == RECEIVER_WAIT_COUNTER_SEND)
                    // new state from counting to counter ack -> thus we send counter already
                    else if (meta.fancy_state.prev_state == RECEIVER_COUNTING && meta.fancy_state.next_state == RECEIVER_COUNTER_ACK) {
                        send_counter();
                    }

                    /* this can happen because of two different things: stop or counter expires */
                    /* Special transition that needs to be done differently if the packet is a control or normal traffic */
                    /* Same than above */
                    else if (meta.fancy_state.prev_state == RECEIVER_COUNTER_ACK && meta.fancy_state.next_state == RECEIVER_COUNTER_ACK) {
                        if (meta.fancy_bridged.entered_as_control == 1) {
                            /* sends counter */
                            send_counter();
                        }   
                        else {
                            /* Clone packet i2e and, one if normally forwarded, the other is used to reply */
                            send_counter_i2e();
                        }
                    }

                    else if (meta.fancy_state.prev_state == RECEIVER_COUNTER_ACK && meta.fancy_state.next_state == RECEIVER_IDLE) {
                        /* Nothing to do */
                        drop_exit_ingress();
                    }

                    else if (meta.fancy_state.prev_state == RECEIVER_COUNTER_ACK && meta.fancy_state.next_state == RECEIVER_COUNTING) {
                        /* Send start ack */
                        send_start_ack();
                    }                
                }
            }
        }
        // Zooming Ingress
        else {

            /* Read State */
            meta.fancy.current_state = read_in_state.execute(meta.fancy.simple_address);

            /* This can be done with the internal traffic generator*/
            /* Forwards a STOP message to the egress machine */
            /* HARDCODED FOR THE CASE STUDY: to do it better use a table to forward STOPS to each port */
            #ifdef HARDWARE
            if ((ig_intr_md.ingress_port == PORT4_S || ig_intr_md.ingress_port[6:0] == RECIRCULATION_PORT) && hdr.fancy.isValid() && hdr.fancy.action_value == STOP)
            {   
                // go to egress directly
                ig_tm_md.ucast_egress_port = PORT1_S
                ;
                exit;
            }
            #else
            if ((ig_intr_md.ingress_port == PORT4_M || ig_intr_md.ingress_port[6:0] == RECIRCULATION_PORT) && hdr.fancy.isValid() && hdr.fancy.action_value == STOP)
            {   
                // go to egress directly
                ig_tm_md.ucast_egress_port = PORT1_M
                ;
                exit;
            }
            #endif
        
            // Read counters and Send counters back
            // Only do if in counting state and receive a STOP, but we will need a SUBCOUNTING STATE
            if (hdr.fancy.isValid() && (hdr.fancy.action_value == GENERATING_MULTIPLE_COUNTERS || hdr.fancy.action_value == STOP)) {
                // for the first packet we add the header
                if (!hdr.fancy_counters_length.isValid()) {
                    set_generating_multiple_counters();
                }

                //  build counter packet 
                // so we can do the comparision 
                if (hdr.fancy_counters_length._length != COUNTER_NODE_WIDTH) {
                    // Increase fancy_counters_length and append one counter
                    add_fancy_counter();

                    // recirculate
                    same_pipe_recirculate();
                    exit;
                } 
                else {
                    // Send it back to the original port it came in
                    return_counter();
                }
            }

            // This sends always the packet to the egress, and shpuld not use it to count anything
            // This happens when the other ingress has sent us a packet with counters, we will process them
            else if (hdr.fancy.isValid() && hdr.fancy.action_value == MULTIPLE_COUNTERS && hdr.fancy.fsm == 1) {
                // pre pare header
                if (!hdr.fancy_pre.isValid()){
                    _set_computing_multiple_counters();
                }
                // subtract 1 to length and remove header already (if we dont have stage move this down)
                // do not substract if its < 0, a saturating field did not work..
                if (hdr.fancy_counters_length._length != 0){
                    hdr.fancy_counters_length._length = hdr.fancy_counters_length._length - 1;
                }
                // Recirculate packet (until it has to be dropped)
                same_pipe_recirculate();
                //ig_tm_md.ucast_egress_port[6:0] = RECIRCULATION_PORT;
            }
        
            // This is our main counting part, this can only be done if at counting and count flag is set.
            else if (hdr.ipv4.isValid() && meta.fancy.current_state == RECEIVER_COUNTING && hdr.fancy.isValid() && hdr.fancy.count_flag == 1) {
                // count ingress side packets
                // the register offet is stored in the counter
                increase_in_counter.execute((bit<10>)meta.fancy.counter_address);
            }


        }
    }
}   
        
/*********************  D E P A R S E R  ************************/

control IngressDeparser(packet_out pkt,
    /* User */
    inout my_ingress_headers_t                       hdr,
    in    my_ingress_metadata_t                      meta,
    /* Intrinsic */
    in    ingress_intrinsic_metadata_for_deparser_t  ig_dprsr_md)
{   

    Resubmit() resubmit;
    Mirror() mirror;

    apply {

        // Resubmit to update ingress state //
        if (ig_dprsr_md.resubmit_type == STATE_UPDATE_INGRESS)
        {
            resubmit.emit<fancy_resubmit_state_meta_h>({
                meta.fancy_state.prev_state, meta.fancy_state.next_state, 
                0,  meta.fancy_state.state_change, meta.fancy_state.state_change_counter,
                meta.fancy_state.control_type, meta.fancy_bridged.packet_id, 0, meta.fancy_bridged.is_dedicated
            });
        }

        if (ig_dprsr_md.mirror_type == INGRESS_SEND_COUNTER)
        {
            mirror.emit<fancy_ingress_mirror_h>(meta.fancy.mirror_session,{
                meta.fancy.mirror_header_type, meta.fancy.local_counter_in, meta.fancy_bridged.packet_id, 0, 
                meta.fancy_bridged.is_internal, 0, meta.fancy_state.control_type, 0, meta.fancy_bridged.is_dedicated}
                );   
        }

        pkt.emit(meta.fancy_bridged);
        pkt.emit(hdr);
    }
}


/*************************************************************************
 ****************  E G R E S S   P R O C E S S I N G   *******************
 *************************************************************************/

/***********************  H E A D E R S  ************************/

struct my_egress_headers_t {
    ethernet_h ethernet;
    fancy_pre_h fancy_pre; // this is kind of a bridge/recirc meta
    fancy_h fancy;
    fancy_counters_length_h fancy_counters_length;
    fancy_counter_h fancy_counter;
    ipv4_h ipv4;
    //tcp_h tcp;
    //udp_h udp;
}

/********  G L O B A L   E G R E S S   M E T A D A T A  *********/

struct my_egress_metadata_t {
    fancy_bridged_meta_h fancy_bridged;
    fancy_state_meta_h fancy_state;
    fancy_egress_meta_h fancy;
}

    /***********************  P A R S E R  **************************/

parser EgressParser(packet_in        pkt,
    /* User */
    out my_egress_headers_t          hdr,
    out my_egress_metadata_t         meta,
    /* Intrinsic */
    out egress_intrinsic_metadata_t  eg_intr_md)
{
    /* This is a mandatory state, required by Tofino Architecture */
    header_type_t packet_type;

    state start {
        pkt.extract(eg_intr_md);

        // all meta to 0
        //meta.fancy_state.prev_state = 0;
        meta.fancy_state.prev_state = 0;
        meta.fancy_state.control_type = 0;
        meta.fancy_state.next_state = 0;
        meta.fancy_state.state_change = 0;
        meta.fancy_state.state_change_counter = 0;

        meta.fancy.current_counter = 0;
        meta.fancy.current_state = 0;
        meta.fancy.lock_status = 0;
        meta.fancy.local_counter_out = 0;
        meta.fancy.local_counter_in = 0;
        meta.fancy.mirror_session = 0;
        meta.fancy.mirror_header_type = 0;

        // zooming clears
         meta.fancy.max_0 = 0;
         meta.fancy.max_1 = 0;
         meta.fancy.zooming_stage = 0;
         meta.fancy.local_counter_and_diff = 0;
         meta.fancy.counter_diff_excess = 0;
    
        // check type
        packet_type = pkt.lookahead<header_type_t>();
        transition select(packet_type) {
            HEADER_NORMAL: parse_bridge;
            HEADER_I2E_MIRRORING: parse_i2e_mirroring;
            HEADER_E2E_MIRRORING: parse_e2e_mirroring;
            HEADER_REROUTE_MIRRORING: parse_reroute_mirroring;
            default: reject;
        }
    }

    state parse_bridge {
        pkt.extract(meta.fancy_bridged);
        transition parse_ethernet;
    }

    state parse_i2e_mirroring {
        //lookahead and copy
        meta.fancy_bridged.setValid();
        meta.fancy_bridged.entered_as_control = 0;

        fancy_ingress_mirror_h i2e_h;
        i2e_h = pkt.lookahead<fancy_ingress_mirror_h>();

        meta.fancy_bridged.header_type = HEADER_I2E_MIRRORING;
        meta.fancy.local_counter_in = i2e_h.local_counter_in;
        meta.fancy_bridged.packet_id = i2e_h.packet_id;
        meta.fancy_bridged.is_internal = i2e_h.is_internal;
        meta.fancy_state.control_type = i2e_h.control_type;
        meta.fancy_bridged.is_dedicated = i2e_h.is_dedicated;

        pkt.advance(FANCY_INGRESS_MIRROR_SIZE);
        transition parse_ethernet;
    }

    state parse_e2e_mirroring {

        meta.fancy_bridged.setValid();
        meta.fancy_bridged.entered_as_control = 0;

        fancy_mirror_state_meta_h e2e_h;
        e2e_h = pkt.lookahead<fancy_mirror_state_meta_h>();
        // copy values to general header

        meta.fancy_bridged.header_type = HEADER_E2E_MIRRORING;

        meta.fancy_bridged.packet_id = e2e_h.packet_id;
        meta.fancy_bridged.is_dedicated = e2e_h.is_dedicated;
        meta.fancy_state.prev_state = e2e_h.prev_state;
        meta.fancy_state.next_state = e2e_h.next_state;
        meta.fancy_state.state_change = e2e_h.state_change;
        meta.fancy_state.state_change_counter = e2e_h.state_change_counter;
        meta.fancy_state.control_type = e2e_h.control_type;
        
        pkt.advance(FANCY_EGRESS_MIRROR_SIZE);

        transition parse_ethernet;
    }

    state parse_reroute_mirroring {

        meta.fancy_bridged.setValid();
        meta.fancy_bridged.entered_as_control = 0;

        fancy_reroute_mirror_h reroute_h;
        reroute_h = pkt.lookahead<fancy_reroute_mirror_h>();
        // copy values to general header

        meta.fancy_bridged.header_type = HEADER_REROUTE_MIRRORING;

        meta.fancy_bridged.packet_id = reroute_h.packet_id;
        meta.fancy_bridged.is_dedicated = reroute_h.is_dedicated;
        
        meta.fancy_bridged.is_internal = reroute_h.is_internal;
        meta.fancy_state.control_type = reroute_h.control_type;
        meta.fancy.original_port = reroute_h.original_port;
        
        pkt.advance(FANCY_REROUTE_MIRROR_SIZE);

        transition parse_ethernet;
    }

    state parse_ethernet {
        // parse porn metadata
        pkt.extract(hdr.ethernet);
        transition select(hdr.ethernet.ether_type) {
            ether_type_t.IPV4 : parse_ipv4;
            ether_type_t.FANCY: parse_fancy;
            ether_type_t.FANCY_PRE: parse_fancy_pre;
            default : accept;
        }
    }

    state parse_fancy_pre {
        pkt.extract(hdr.fancy_pre);
        transition parse_fancy;
    }

    state parse_fancy {
        pkt.extract(hdr.fancy);
        transition select(hdr.fancy.nextHeader, hdr.fancy.action_value)
        {
            (ether_type_t.IPV4, _): parse_ipv4;
            (_, MULTIPLE_COUNTERS_PARSER): parse_fancy_counters_length_and_counter;
            (_, GENERATING_MULTIPLE_COUNTERS_PARSER): parse_fancy_counters_length;
            default: accept;
        }
    }

    state parse_fancy_counters_length_and_counter{
        pkt.extract(hdr.fancy_counters_length);
        pkt.extract(hdr.fancy_counter);
        transition accept;
    }

    state parse_fancy_counters_length {
        pkt.extract(hdr.fancy_counters_length);
        transition accept;
    }

    state parse_ipv4 {
        pkt.extract(hdr.ipv4);
        transition accept;
    }

}

    /***************** M A T C H - A C T I O N  *********************/

control Egress(
    /* User */
    inout my_egress_headers_t                          hdr,
    inout my_egress_metadata_t                         meta,
    /* Intrinsic */
    in    egress_intrinsic_metadata_t                  eg_intr_md,
    in    egress_intrinsic_metadata_from_parser_t      eg_prsr_md,
    inout egress_intrinsic_metadata_for_deparser_t     eg_dprsr_md,
    inout egress_intrinsic_metadata_for_output_port_t  eg_oport_md)
{
    /* Actions */
    /* drop 3-bit field:
    [2]-> disable mirroring
    [1]-> disable copy_to_cpu
    [0]-> disable unicast, multicast or resubmit
    */
    action drop_exit_egress () {
        eg_dprsr_md.drop_ctl = 3w1;
        exit;
    }

    action drop_egress () {
        eg_dprsr_md.drop_ctl = 1;
    }

    action set_dedicated_addres() {
        // get dedicated address
        meta.fancy.dedicated_address = meta.fancy.port_address_offset + meta.fancy_bridged.packet_id;
    }

    // State, and state actions
    #include "dedicated_egress.p4"
    #include "zooming_egress.p4"

    apply {

        // set src mac 
        // debugging so the link.py works
        hdr.ethernet.src_addr = (mac_addr_t)eg_intr_md.egress_port;

        //exit;
        /* Egress State Machine: Represents the sending side */
        /* Obtain addressing properties for this packet */
        egress_port_info.apply();

        // IMPORTANT: WE CAN MER
        // TO: by setting the address in a table and action parameter for the simple
        // set base adress 
        out_port_to_offsets.apply();

        // Set dedicated counters final address
        set_dedicated_addres();

        // @bridged thing
        // 
        /* Comes from the other switch */
        if (meta.fancy_bridged.is_dedicated == 1) { 
            if (meta.fancy_bridged.is_internal == 0) {
                if (meta.fancy.egress_type == FANCY_SWITCH) {
                    /* Addressing */
                    // get main address
                    //set_dedicated_addres();
                    //meta.fancy.dedicated_address = meta.fancy.port_address_offset + meta.fancy_bridged.packet_id;   

                    //We need to get the memory index for this packet SM */
                    //if (!hdr.fancy.isValid()) {
                    //    /* computes the address using meta.packet_id */
                    //    meta.fancy.dedicated_address = meta.fancy.port_address_offset + meta.fancy_bridged.packet_id;
                    //}
                    //else {
                    //    /* Computes the address using fancy.id */
                    //    /* This is needed for only control plane packets since they
                    //    dont have IP maybe */
                    //    meta.fancy.dedicated_address = meta.fancy.port_address_offset + hdr.fancy.id;
                    //}

                    /* Stage 0 */
                    /* Read and update state */
                    meta.fancy.current_state = read_update_state_out.execute(meta.fancy.dedicated_address);
                    meta.fancy.current_counter = update_counter_out.execute(meta.fancy.dedicated_address);

                    /* Compute next state */
                    /* If control type is not 0 we dont check this */
                    if (meta.fancy_state.control_type == 0) {
                        /* If its a control packet and did not hit the table we drop it  inmediately */
                        /* control packets that do not hit, they got lost maybe? */
                        if (table_next_state_out.apply().miss) {
                            if (meta.fancy_bridged.entered_as_control == 1) {
                                drop_exit_egress();
                            }                    
                        }
                    }

                    /* Lock state or check if state is locked */
                    meta.fancy.lock_status = read_update_state_lock_out.execute(meta.fancy.dedicated_address);


                    /* STATE MACHINE LOGIC */
                    /* If state was locked now, we resubmit */
                    if (meta.fancy.lock_status == LOCK_OBTAINED){
                        /* Enable packet resubmit */ 
                        mirror_to_update();
                        
                    }   
                    else if (meta.fancy.lock_status == LOCK_RELEASED) {
                        /* State transitions */
                        
                        /* From idle to counting */
                        if (meta.fancy_state.prev_state == SENDER_IDLE && meta.fancy_state.next_state == SENDER_IDLE) {
                            /* sends counter ack again */
                            send_counter_ack();
                        } 
                        else if (meta.fancy_state.prev_state == SENDER_IDLE && meta.fancy_state.next_state == SENDER_START_ACK) {
                            /* sends start packet: checks if it has to add a header or not */
                            table_idle_to_start_ack_out.apply();
                        }
                        /* This can happen when the receiver sends us a very late counter, we just ACK it, and reset all again */
                        /* The transition below is the one that does the rentransmission when the START ACK never arrived */                    
                        else if (meta.fancy_state.prev_state == SENDER_START_ACK && meta.fancy_state.next_state == SENDER_START_ACK && meta.fancy_state.state_change_counter == 0) {
                            /* Sends COUNTER ACK eventough the nameing might be confusing */
                            send_counter_ack();   
                        }
                        /* This one means that this is a transition made by a counterr reaching some value, i guess this is to send a retransmission */
                        /* plus is a way to differenciate with the previous transition which has the same src dst states*/                    
                        else if (meta.fancy_state.prev_state == SENDER_START_ACK && meta.fancy_state.next_state == SENDER_START_ACK && meta.fancy_state.state_change_counter == 1) {
                            table_start_ack_to_start_ack_out.apply();
                        }
                        else if (meta.fancy_state.prev_state == SENDER_START_ACK && meta.fancy_state.next_state == SENDER_COUNTING) {
                            /* received the start ack from receiver */
                            drop_exit_egress();
                        }
                        else if (meta.fancy_state.prev_state == SENDER_COUNTING && meta.fancy_state.next_state == SENDER_WAIT_COUNTER_RECEIVE) {
                            /* send counter */
                            table_counting_to_wait_counter.apply();
                        }
                        /* HERE IS WHERE WE WOULD MOVE TO A COMPUTE STATE INSTEAD */
                        else if (meta.fancy_state.prev_state == SENDER_WAIT_COUNTER_RECEIVE && meta.fancy_state.next_state == SENDER_IDLE) {
                            send_counter_ack();
                        } 
                        /* Skip idle state directly jump to sender start ack*/
                        else if (meta.fancy_state.prev_state == SENDER_WAIT_COUNTER_RECEIVE && meta.fancy_state.next_state == SENDER_START_ACK) {
                            /* sends start */
                            table_wait_counter_to_start_ack.apply();
                        }
                        else if (meta.fancy_state.prev_state == SENDER_WAIT_COUNTER_RECEIVE && meta.fancy_state.next_state == SENDER_WAIT_COUNTER_RECEIVE) {
                            /* retransmit stop  */
                            table_wait_counter_to_wait_counter.apply();
                        }                                                                                                                                       
                    }
                }

                /* END OF EGRESS STATE MACHINELOGIC */
                /* This is done to drop the original control packet. When a state
                update is needed a e2e clone is performed to update the state
                however the original control packet is not needed anymore */
                if (meta.fancy_bridged.entered_as_control == 1 && meta.fancy_bridged.header_type == HEADER_NORMAL && meta.fancy_state.state_change == 1) {
                    drop_exit_egress();
                }
                /* I am sure this needs more flags to be checked, for example cloned packets will have to be treated in some special way */
                /* Need to make sure that only packets that will leave the switch enter here... CHECKING THE LOCK IS NOT IMPORTANT BUT....*/
                /* and meta.lock_status != LOCK_NONE : this is removed because normal packets also see the lock blocked*/
                /* This makes the thing count some extra packets while the state is being updated */            
                else if (meta.fancy.egress_type == FANCY_SWITCH && meta.fancy.current_state == SENDER_COUNTING && hdr.ipv4.isValid()) {
                    if ((hdr.fancy.isValid())) {
                        hdr.fancy.count_flag = 1;
                        meta.fancy.counter_update_type_out = COUNTER_INCREASE;
                    }
                    /* Add header and count flag */
                    else {
                        add_egress_fancy_header();
                    }
                }
                else if (meta.fancy.egress_type != FANCY_SWITCH && hdr.fancy.isValid()) {
                    hdr.ethernet.ether_type = hdr.fancy.nextHeader;
                    hdr.fancy.setInvalid(); // Invalidate?
                }

                /*COUNT PACKET */
                /* Count for this packet */
                /* Or reset, depending on the packet transition in the state machine */
                /* also reads the coubter */
                meta.fancy.local_counter_out = increase_pkt_counters_out.execute(meta.fancy.dedicated_address);

                /* Here we do the counter difference logic, before reporting the counter */
                /* we do this here because before we did not have the counter value */
                /* Special transition! */
                if (meta.fancy.lock_status == LOCK_RELEASED && (meta.fancy_state.prev_state == SENDER_WAIT_COUNTER_RECEIVE && 
                    (meta.fancy_state.next_state == SENDER_IDLE || meta.fancy_state.next_state == SENDER_START_ACK))) {

                    /* Counter difference */
                    /* We set the counter diff to fancy.counter_value in the ACK message just for debugging */
                    hdr.fancy.counter_value = meta.fancy.local_counter_out - hdr.fancy.counter_value;

                    // if fancy.counter_value != 0 we report this to the ingress to do that 
                    // we use e2e clone and we clone to recirc port
                    #ifdef REROUTE
                    if (hdr.fancy.counter_value != 32w0)
                    {   
                        
                        clone_to_recirculation.apply();
                    }
                    #endif
                    
                }
            }

            /* Special cloned packets from the ingress for which we need to add a FANCY header and some data */
            /* We need to do this when we need to generate a control packet from normal traffic */
            else if (meta.fancy_bridged.is_internal == 1w1 && meta.fancy_state.control_type == INGRESS_SEND_COUNTER && meta.fancy_bridged.header_type == HEADER_I2E_MIRRORING) {
                add_fancy_counter_header();
            }
            
            #ifdef REROUTE
            /* re route recirculated packet to send to ingress */
            else if (meta.fancy_bridged.is_internal == 1w1 && meta.fancy_state.control_type == REROUTE_RECIRCULATE && meta.fancy_bridged.header_type == HEADER_REROUTE_MIRRORING) {
                add_fancy_pre_header();
            }
            #endif
        }
        else {
            // Always read or try to update
            update_read_zooming_stage();
        
            read_update_max_0();
            read_update_max_1();

            /* For the experiment we will need to update this when 
            we see STOPS or at the end counter compute exchanges */
            read_out_state();

            // if we have received counters
            if (hdr.fancy.isValid() && hdr.fancy.action_value == MULTIPLE_COUNTERS) {

                // this means that there is no counters
                if (hdr.fancy_pre.isValid() && ((hdr.fancy_pre.pre_type & 0x20) != 0)) {
                    drop_egress();
                }

                else if (hdr.fancy_counters_length.isValid()) {
                    // Read and reset local counter -> can be reset since the packet 
                    // was received, and we can use this for the next round.
                    read_reset_counter();

                    // subtracts local and remote counter to see packet difference
                    //meta.fancy.local_counter_and_diff = meta.fancy.local_counter_and_diff |-| hdr.fancy_counter.counter_value;
                    //hdr.fancy_counter.setInvalid();
                    subtract_counters();
                    //apply(subtract_counters);

                    // Last layer drops
                    if (meta.fancy.zooming_stage == MAX_ZOOM && meta.fancy.local_counter_and_diff != 0)
                    {
                        build_hash_path();
                    }

                    // if the difference is bigger than the previous counter diff excess will be 0
                    subtract_differences();
                    

                    // update max values from the packet header fancy_pre
                    if (meta.fancy.counter_diff_excess == 32w0) 
                    {
                        hdr.fancy_pre.max_index = hdr.fancy_counters_length._length;
                        hdr.fancy_pre.max_counter_diff = meta.fancy.local_counter_and_diff;
                    }        
                    
                    // sets packet to update zooming, max, etc
                    set_fancy_pre_type_to_update.apply();                
                }
            }

            // egress counting stuff
            else if (hdr.ipv4.isValid() && meta.fancy.current_state == SENDER_COUNTING) {

                // if no header
                if (!hdr.fancy.isValid()) {
                    // add header
                    add_fancy_counting_header();
                }

                // if we are at the root
                if (meta.fancy.zooming_stage == 0) {
                    set_zoom_address_0();
                }
                else if (meta.fancy.zooming_stage == 1 && meta.fancy.max_0 == meta.fancy_bridged.hash_0) {
                    set_zoom_address_1();
                }
                else if (meta.fancy.zooming_stage == 2 && meta.fancy.max_0 == meta.fancy_bridged.hash_0 && 
                                                                meta.fancy.max_1 == meta.fancy_bridged.hash_1) {
                    set_zoom_address_2();
                }

                // counting
                if (meta.fancy.count_packet_flag == 1)
                {
                    //count
                    _add_to_counter();
                }
                else {
                    remove_fancy_header();
                }

            }

            else if (hdr.fancy.isValid() && hdr.ipv4.isValid() && meta.fancy.current_state == 0) {
                // remove just in case we are not counting
                remove_fancy_header();
            }

        }
    }
}

    /*********************  D E P A R S E R  ************************/

control EgressDeparser(packet_out pkt,
    /* User */
    inout my_egress_headers_t                       hdr,
    in    my_egress_metadata_t                      meta,
    /* Intrinsic */
    in    egress_intrinsic_metadata_for_deparser_t  eg_dprsr_md)
{
    // checksum
    Checksum() ipv4_checksum;

    // mirroring
    Mirror() mirror;

    apply {
        if (hdr.ipv4.isValid())
        {
            hdr.ipv4.hdr_checksum = ipv4_checksum.update({
                hdr.ipv4.version,
                hdr.ipv4.ihl,
                hdr.ipv4.tos,
                hdr.ipv4.total_len,
                hdr.ipv4.identification,
                hdr.ipv4.flags,
                hdr.ipv4.frag_offset,
                hdr.ipv4.ttl,
                hdr.ipv4.protocol,
                hdr.ipv4.src_addr,
                hdr.ipv4.dst_addr
            });
        }

        if (eg_dprsr_md.mirror_type == STATE_UPDATE_EGRESS){
            mirror.emit<fancy_mirror_state_meta_h>(meta.fancy.mirror_session, {meta.fancy.mirror_header_type,  meta.fancy_state.prev_state, 
            meta.fancy_state.next_state, 0, meta.fancy_state.state_change, meta.fancy_state.state_change_counter,
            meta.fancy_state.control_type, meta.fancy_bridged.packet_id, 0, meta.fancy_bridged.is_dedicated});
        }
        if (eg_dprsr_md.mirror_type == REROUTE_RECIRCULATE){
            mirror.emit<fancy_reroute_mirror_h>(meta.fancy.mirror_session, {meta.fancy.mirror_header_type, meta.fancy_bridged.packet_id, 0, 
            meta.fancy_bridged.is_internal, 0, meta.fancy_state.control_type, 0, meta.fancy.original_port, 0, meta.fancy_bridged.is_dedicated});
        }

        pkt.emit(hdr);
    }
}


/************ F I N A L   P A C K A G E ******************************/
Pipeline(
    IngressParser(),
    Ingress(),
    IngressDeparser(),
    EgressParser(),
    Egress(),
    EgressDeparser()
) pipe;

// @pa_auto_init_metadata
Switch(pipe) main;
