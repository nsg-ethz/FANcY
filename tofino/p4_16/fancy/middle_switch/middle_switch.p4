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


#include "../includes/constants.p4"
#include "../includes/headers.p4"



/*************************************************************************
 **************  I N G R E S S   P R O C E S S I N G   *******************
 *************************************************************************/

/***********************  H E A D E R S  ************************/

struct my_ingress_headers_t {
    ethernet_h ethernet;
    fancy_h fancy;
    ipv4_h ipv4;
}


/******  G L O B A L   I N G R E S S   M E T A D A T A  *********/
struct my_ingress_metadata_t {
    bit<16> drop_prefix_index;
    bit<32> drop_rate;
    bit<1> drop_packet;
    bit<1> drop_prefix_enabled;
    bit<1> reroute_enabled;
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
        meta = {0, 0, 0, 0, 0};
        transition parse_ethernet;
    }
    
    state parse_ethernet {
        // parse port metadata
        pkt.advance(PORT_METADATA_SIZE);
        pkt.extract(hdr.ethernet);
        transition select(hdr.ethernet.ether_type) {
            ether_type_t.IPV4 : parse_ipv4;
            ether_type_t.FANCY: parse_fancy;
            default : accept;
        }
    }

    state parse_fancy {
        pkt.extract(hdr.fancy);
        transition select(hdr.fancy.nextHeader)
        {
            ether_type_t.IPV4: parse_ipv4; 
            default: accept;
        }
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
        size = 512;
        default_action = NoAction();
    }

    table forward_after {
        key = {
            ig_intr_md.ingress_port: exact;
        }
        actions = {
            set_port; 
            @defaultonly NoAction;
        }
        size = 512;
        default_action = NoAction();
    }


    Register<bit<1>, bit<1>>(1, 0) reroute_enabled;
    RegisterAction<bit<1>, bit<1>, bit<1>>(reroute_enabled)
    set_reroute = {
        void apply(inout bit<1> value, out bit<1> rv) {
            value = 1;
            rv = value;
        }
    };
    RegisterAction<bit<1>, bit<1>, bit<1>>(reroute_enabled)
    clear_reroute = {
        void apply(inout bit<1> value, out bit<1> rv) {
            value = 0;
            rv = value;
        }
    };
    RegisterAction<bit<1>, bit<1>, bit<1>>(reroute_enabled)
    read_reroute = {
        void apply(inout bit<1> value, out bit<1> rv) {
            rv = value;
        }
    };


    action set_reroute_enabled () {
        meta.reroute_enabled = set_reroute.execute(0);
    }

    action enable_drop (bit<16> drop_prefix_index) {
        meta.drop_prefix_index = drop_prefix_index;
        meta.drop_prefix_enabled = 1;
    }

    table can_be_dropped {
        key = {
            hdr.ipv4.dst_addr: exact;
        }
        actions = {
            enable_drop; 
            @defaultonly NoAction;
        }
        size = 512;
        default_action = NoAction();
    }

    Random<bit<32>>() random;

    Register<bit<32>, bit<16>>(1000, 0) loss_rates;
    RegisterAction<bit<32>, bit<16>, bit<1>>(loss_rates)
    check_if_loss = {
        void apply(inout bit<32> value, out bit<1> rv) {

            if (meta.drop_rate < value)
            {
                rv = 1;
            }
            else {
                rv = 0;
            }
        }
    };


    Register<bit<32>, bit<16>>(1000, 0) loss_count;
    RegisterAction<bit<32>, bit<16>, bit<32>>(loss_count)
    count_loss = {
        void apply(inout bit<32> value) {
            value = value + 1;
        }
    };


    action check_if_drop (){
        meta.drop_packet = check_if_loss.execute(meta.drop_prefix_index);
    }

    apply {

        // Drop all LLDP packets. 
        if (hdr.ethernet.isValid() && hdr.ethernet.ether_type == ether_type_t.LLDP) {
            drop_exit_ingress();
        }

        // check if ingress port is the rerouted port so we enable the thingy
        if (ig_intr_md.ingress_port == PORT6_S) {
            meta.reroute_enabled = set_reroute.execute(0);
        }
        else if (ig_intr_md.ingress_port == PORT1_S) {
            meta.reroute_enabled = clear_reroute.execute(0);
        }
        else {
            meta.reroute_enabled = read_reroute.execute(0);
        }

        // Drops table
        can_be_dropped.apply();

        // we only drop coming from port PORT1_S
        /* Also we do not drop control packets */

        if (((hdr.ipv4.isValid() && !hdr.fancy.isValid()) || (hdr.fancy.isValid() && hdr.fancy.action_value == KEEP_ALIVE)) && 
            (ig_intr_md.ingress_port == PORT1_S) && meta.drop_prefix_enabled == 1) {

                // get random number
                meta.drop_rate = random.get();
                check_if_drop();

                if (meta.drop_packet == 1) {
                    count_loss.execute(meta.drop_prefix_index);
                    drop_exit_ingress();
                }
        }

        /* Forwarding or Reroute */
        if (meta.reroute_enabled == 0){
            forward.apply();
        }
        else {
            forward_after.apply();
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

    apply {

        pkt.emit(hdr);
    }
}


/*************************************************************************
 ****************  E G R E S S   P R O C E S S I N G   *******************
 *************************************************************************/

/***********************  H E A D E R S  ************************/

struct my_egress_headers_t {

}

/********  G L O B A L   E G R E S S   M E T A D A T A  *********/

struct my_egress_metadata_t {

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
 
    apply {
        
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

    apply {

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
