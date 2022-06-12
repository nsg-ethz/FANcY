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

/* Common actions */
action _NoAction() {
    no_op();
}

metadata fancy_meta_t meta;

//@pragma pa_solitary ingress meta.local_counter_in
//@pragma pa_solitary egress meta.local_counter_in
//@pragma pa_solitary egress meta.local_counter_out
@pragma pa_no_overlay egress meta.local_counter_in
@pragma pa_no_overlay egress meta.local_counter_out

//header_type bridged_meta_t {
//    fields {
//    }
//}
//
//header_type ingress_meta_t {
//    fields {
//
//    }
//}
//
//header_type egress_meta_t {
//    fields {
//
//    }
//}

#include "fancy_ingress.p4"
#include "fancy_egress.p4"

//metadata ingress_meta_t ing_meta;
//metadata egress_meta_t egr_meta;
//metadata bridged_meta_t br_meta;

control ingress {
  ingress_ctrl();
}

control egress {
  egress_ctrl();
}