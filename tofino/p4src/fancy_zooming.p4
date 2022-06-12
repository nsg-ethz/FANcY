/* -*- P4_14 -*- */

#ifdef __TARGET_TOFINO__
#include <tofino/constants.p4>
#include <tofino/intrinsic_metadata.p4>
#include <tofino/primitives.p4>
#include <tofino/stateful_alu_blackbox.p4>
#else
#error This program is intended to compile for Tofino P4 architecture only
#endif

#include "includes/constants.p4"
#include "includes/headers.p4"
#include "includes/parser.p4"

/*** Common Utils ***/

//@pragma pa_container_size ingress fancy_counters_length._length 8
//@pragma pa_atomic ingress fancy.counter_value
//@pragma pa_container_size egress fancy.counter_value 32
//@pragma pa_container_size egress meta.hash_0 16
//@pragma pa_container_size egress meta.hash_1 16
//@pragma pa_container_size egress meta.hash_2 16
//@pragma pa_container_size egress meta.counter_address 32
//@pragma pa_container_size egress fancy.seq 16
//@pragma pa_container_size egress meta.counter_address 8 8 
//@pragma pa_solitary egress fancy_pre.pre_type
//@pragma pa_container_size egress fancy_pre.pre_type 16

action _NoAction() {
    no_op();
}

header_type bridged_meta_t {
    fields {
        hash_0: 16;
        hash_1: 16;
        hash_2: 16;
    }
}


#include "fancy_zooming_ingress.p4"
#include "fancy_zooming_egress.p4"

@pragma pa_no_overlay ingress ipv4.dstAddr

metadata ingress_meta_t ing_meta;
metadata egress_meta_t egr_meta;
metadata bridged_meta_t br_meta;

control ingress {
  ingress_ctrl();
}

control egress {
  egress_ctrl();
}