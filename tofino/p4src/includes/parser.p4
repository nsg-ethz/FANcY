header ethernet_t   ethernet;
header ipv4_t       ipv4;
header fancy_pre_t fancy_pre;
header fancy_t       fancy;
header fancy_counters_length_t fancy_counters_length;
header fancy_counter_t fancy_counter;
header tcp_t        tcp;
header udp_t        udp;

/* PARSER */

#define IPV4_ACTION 65536 //0b000010000000000000000 // 0x0800 << 5 bits for the ACTION
#define MULTIPLE_COUNTERS_PARSER 16 //0b000000000000000010000 // 16 zeros + 0b10000
#define GENERATING_MULTIPLE_COUNTERS_PARSER 8 //0b000000000000000001000 // 8 zeros + 0b10000

parser start {
    return parse_ethernet;
}

parser parse_ethernet {
    extract(ethernet);
    //set_metadata(meta.counter_address, 0);
    //set_metadata(meta.simple_address, 0);
    return select(ethernet.etherType) {
        IPV4 : parse_ipv4;
        FANCY : parse_fancy;
        FANCY_PRE: parse_fancy_pre;
        default: ingress;
    }
}

parser parse_fancy_pre {
    extract(fancy_pre);
    return parse_fancy;
}

//return select(fancy.nextHeader, fancy.count_flag, fancy.ack, fancy.fsm, fancy.action_value) {
parser parse_fancy {
    extract(fancy);
    return select(fancy.nextHeader, fancy.action_value) {
        IPV4_ACTION mask 2097144 : parse_ipv4; // bits 0b111111111111111111000
        MULTIPLE_COUNTERS_PARSER mask 31 : parse_dfpd_counters_length_and_counter; //0b000000000000000011111
        GENERATING_MULTIPLE_COUNTERS_PARSER mask 31 : parse_dfpd_counters_length; //0b000000000000000011111
        default: ingress;
    }
}

parser parse_dfpd_counters_length {
    extract(fancy_counters_length);
    return ingress;
}

parser parse_dfpd_counters_length_and_counter {
    extract(fancy_counters_length);
    extract(fancy_counter);
    return ingress;
}

parser parse_ipv4 {
    extract(ipv4);
    return select(ipv4.protocol) {
        TCP : parse_tcp;
        UDP : parse_udp;
        default: ingress;
    }
}

parser parse_tcp {
    extract(tcp);
    return ingress;
}

parser parse_udp {
    extract(udp);
    return ingress;
}

// Update IPV4 Checksum

field_list ipv4_checksum_list {
    ipv4.version;
    ipv4.ihl;
    ipv4.tos;
    ipv4.totalLen;
    ipv4.identification;
    ipv4.flags;
    ipv4.fragOffset;
    ipv4.ttl;
    ipv4.protocol;
    ipv4.srcAddr;
    ipv4.dstAddr;
}

field_list_calculation ipv4_checksum {
    input        { ipv4_checksum_list; }
    algorithm    : csum16;
    output_width : 16;
}

//     verify ipv4_checksum;
calculated_field ipv4.hdrChecksum  {
    update ipv4_checksum;
}
