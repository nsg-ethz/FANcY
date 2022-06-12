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

metadata debug_meta_t meta;

table forward {
  reads { 
    ig_intr_md.ingress_port: exact;
  }
  actions {
    set_port;
    _NoAction;
  }
  default_action: _NoAction();
  size: 64;
}

action drop_exit_ingress() {
  modify_field(ig_intr_md_for_tm.drop_ctl, 1);
  exit();
}

table drop1 {
  actions {
    drop_exit_ingress;
  }
  default_action: drop_exit_ingress ();
}

table drop2 {
  actions {
    drop_exit_ingress;
  }
  default_action: drop_exit_ingress ();
}

action _NoAction() {
    no_op();
}

action set_port(outport)
{
    modify_field(ig_intr_md_for_tm.ucast_egress_port, outport);
}

action mirror_packet() {
  clone_ingress_pkt_to_egress(100);
}

table mirror_packet_table {
  actions {
    mirror_packet;
  }
  default_action: mirror_packet();
}

action do_random() {
    modify_field_rng_uniform(meta.drop_rate, 0, MAX32); //MAX32
}

table get_random {
  actions  {
    do_random;
  }
  default_action: do_random ();
}

action enable_drop (drop_prefix_index){
  modify_field(meta.drop_prefix_index, drop_prefix_index);
  modify_field(meta.drop_prefix_enabled, 1);
}

table can_be_dropped {
    reads { 
      ipv4.dstAddr: exact;
    }
    actions {
      enable_drop;
      _NoAction;
    }
    default_action: _NoAction; /* default to tree*/
    size: 512;
}

register loss_rates {
    width : 32;
    instance_count : 1000;
}

/* stage 0 counter change*/
blackbox stateful_alu check_if_loss {
    reg     : loss_rates;

    condition_lo: meta.drop_rate < register_lo;
    output_value    :   combined_predicate;
    output_dst      :   meta.drop_packet;
}


action a_check_if_drop()
{
  check_if_loss.execute_stateful_alu(meta.drop_prefix_index);
}

table check_if_drop
{
  actions  {
    a_check_if_drop;
  }
  default_action: a_check_if_drop ();
}


register loss_count {
    width : 32;
    instance_count : 1000;
}

/* stage 0 counter change*/
blackbox stateful_alu count_loss {
    reg     : loss_count;

    update_lo_1_value: register_lo + 1;
}

action a_count_loss()
{
  count_loss.execute_stateful_alu(meta.drop_prefix_index);
}

table t_count_loss
{
  actions  {
    a_count_loss;
  }
  default_action: a_count_loss ();
}


control ingress {
    // Forward all packets 4->6
    if (ethernet.etherType == LLDP)
    {
      /// filter LLDP packets so we dont have noise.
      apply(drop1);
    }

    // Drops table
    apply(can_be_dropped);

    // we only drop coming from port PORT1_S
    /* Also we do not drop control packets */
    if (((valid(ipv4) and not valid(fancy)) or (valid(fancy) and fancy.action_value == KEEP_ALIVE)) and (ig_intr_md.ingress_port == PORT1_S) and meta.drop_prefix_enabled == 1)
    { 
      apply(get_random);
      apply(check_if_drop);
//
      if (meta.drop_packet == 1)
      {
        apply(t_count_loss);
        apply(drop2);
      }
    }   
  
    // normal forwarding also send to the controller if needed
    apply(forward) {
      hit {
        // Clone all ingress packets to port 1
        // Only clone very specific packets
        if ((valid(fancy) and (fancy.action_value == COUNTER or fancy.action_value == MULTIPLE_COUNTERS)))
        {
          apply(mirror_packet_table);
        }
      }
    }
}

control egress {

}

