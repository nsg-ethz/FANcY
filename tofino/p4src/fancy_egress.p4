
/* drop 3-bit field:

[2]-> disable mirroring
[1]-> disable copy_to_cpu
[0]-> disable unicast, multicast or resubmit
*/

action drop_exit_egress() {
  modify_field(eg_intr_md_for_oport.drop_ctl, 1);
  exit();
}

action drop_egress() {
  modify_field(eg_intr_md_for_oport.drop_ctl, 1);
}

action strong_drop_egress() {
  modify_field(eg_intr_md_for_oport.drop_ctl, 7);
}

/* Register Definition */

register counters_out {
    width : 32;
    instance_count : NB_REGISTER_SIZE;
}

register pkt_counters_out {
    width : 32;
    instance_count : NB_REGISTER_SIZE; 
}

register state_out {
    width : 8;
    instance_count : NB_REGISTER_SIZE;
}

register state_lock_out {
    width : 8;
    instance_count : NB_REGISTER_SIZE;
}

/* Stateful alus logic */

/* Stage 0 state change*/
blackbox stateful_alu read_update_state_out {
    reg     : state_out;

    condition_lo: meta.control_type == STATE_UPDATE_EGRESS;

    update_lo_1_predicate: not condition_lo;
    update_lo_1_value: register_lo;

    update_lo_2_predicate: condition_lo;
    update_lo_2_value: meta.next_state;

    output_value    :   alu_lo;
    output_dst      :   meta.current_state;
}

/* stage 0 counter change*/
blackbox stateful_alu update_counter_out {
    reg     : counters_out;

    condition_lo: meta.control_type == STATE_UPDATE_EGRESS;

    update_lo_1_predicate: not condition_lo;
    update_lo_1_value: register_lo + 1;

    update_lo_2_predicate: condition_lo;
    update_lo_2_value: 0;

    output_value    :   alu_lo;
    output_dst      :   meta.current_counter;
}

/* Stage 2 state change*/
/* h l
/* 0 0 -> 1 LOCK_NONE
/* 0 1 -> 2 LOCK_RELEASED
/* 1 0 -> 4 LOCK_OBTAINED
/* 1 1 -> 8 LOCK_ERROR
*/
/* Stage 2 state change*/
/* This very specific register does some weird things. It is a bit random and
   I am not sure if it follows any logic. However, for example, when compiling with 
   9.2.0, after a reroute from port 1 to 6, even if condition hi is TRUE, the output of 
   remains 0, while it should be LOCK_OBTAINED, this does not happen in 8.9.2 */
blackbox stateful_alu read_update_state_lock_out {
    reg     : state_lock_out;

    condition_lo: meta.control_type == STATE_UPDATE_EGRESS;
    /* register lo can be either 0 or 10 thus, if  register=0 and state_change=1 */
    condition_hi: register_lo + meta.state_change == 1; 

    update_lo_1_predicate: condition_lo and not condition_hi;
    update_lo_1_value: 0;
    update_lo_2_predicate: condition_hi and not condition_lo;
    update_lo_2_value: LOCK_VALUE;

    //workaround for the broken predicate in SDE 9.2.0
    //update_hi_1_predicate: condition_lo and not condition_hi;
    //update_hi_1_value: LOCK_RELEASED;
    //update_hi_2_predicate: condition_hi and not condition_lo;
    //update_hi_2_value: LOCK_OBTAINED;


    output_value    :   predicate;
    output_dst      :   meta.lock_status;
}

/* Egress Packet counter */
blackbox stateful_alu increase_pkt_counters_out {
    reg     : pkt_counters_out;

    condition_lo: meta.counter_update_type_out == COUNTER_INCREASE;
    condition_hi: meta.counter_update_type_out == COUNTER_RESET;
    
    update_lo_1_predicate: condition_lo;
    update_lo_1_value: register_lo + 1;
    update_lo_2_predicate: condition_hi;
    update_lo_2_value: 0;

    // Returns the previous value before +1 or reset
    output_value    :   register_lo;
    output_dst      :   meta.local_counter_out;
}

action action_packet_count_out() {
  increase_pkt_counters_out.execute_stateful_alu(meta.dedicated_address);
}

table table_packet_count_out {
  actions {
    action_packet_count_out;
  }
  default_action: action_packet_count_out();
}

/* Egress Actions  and tables */

table egress_compute_addresses_no_fancy {
  actions {
    compute_addresses_no_fancy;
  }
  default_action: compute_addresses_no_fancy();
  size: 1;
}

table egress_compute_addresses_fancy {
  actions {
    compute_addresses_fancy;
  }
  default_action: compute_addresses_fancy();
  size: 1;
}

action set_egress_type(egress_type) {
  modify_field(meta.egress_type,egress_type);
}

table egress_fancy_enabled {
  reads {
    eg_intr_md.egress_port: exact;
  }
  actions {
    set_egress_type;
    _NoAction;
  }
  default_action: _NoAction();
  size: 64;
}

action action_read_update_state_out()
{
  read_update_state_out.execute_stateful_alu(meta.dedicated_address);
}

table table_read_update_state_out
{
  actions {
    action_read_update_state_out;
  }
  default_action: action_read_update_state_out();
}

action action_update_counter_out()
{
  update_counter_out.execute_stateful_alu(meta.dedicated_address);
}

table table_update_counter_out
{
  actions {
    action_update_counter_out;
  }
  default_action: action_update_counter_out();
}

action set_next_state_out(next_state, counter_type)
{
  modify_field(meta.next_state, next_state);
  modify_field(meta.prev_state, meta.current_state);
  modify_field(meta.state_change, 1);
  modify_field(meta.state_change_counter, counter_type); 
}

table table_next_state_out
{
  reads{
    meta.current_state: exact;
    meta.current_counter: ternary;
    fancy.action_value: ternary;
    fancy.ack: ternary;
    fancy.fsm: ternary;
    fancy.valid: ternary;
  }
  actions {
    set_next_state_out;
    _NoAction;
  }
  default_action: _NoAction();
}

action action_state_lock_out()
{
  read_update_state_lock_out.execute_stateful_alu(meta.dedicated_address);
}

table table_state_lock_out
{
  actions {
    action_state_lock_out;
  }
  default_action: action_state_lock_out();
}

action action_mirror_to_update(mirror_id) {
  modify_field(meta.control_type, STATE_UPDATE_EGRESS);
  clone_egress_pkt_to_egress(mirror_id, state_update_fields);
}

table table_mirror_to_update {
  reads {
    eg_intr_md.egress_port: exact;
  }
  actions {
    action_mirror_to_update;
    _NoAction;
  }
  default_action: _NoAction();
  size: 512;
}

/* State machine action/tables */

action send_start() {
  add_header(fancy);
  modify_field(fancy.id, meta.packet_id);
  modify_field(fancy.nextHeader, ethernet.etherType);
  modify_field(ethernet.etherType, FANCY);
  modify_field(fancy.action_value, START);
  modify_field(fancy.count_flag, 0);
  modify_field(fancy.ack, 0);
  modify_field(fancy.fsm, 0);
  modify_field(meta.counter_update_type_out, COUNTER_RESET);
}

action send_start_already_fancy() {
  //add_header(fancy);
  //modify_field(fancy.nextHeader, ethernet.etherType);
  //modify_field(ethernet.etherType, FANCY);
  modify_field(fancy.action_value, START);
  modify_field(fancy.count_flag, 0);
  modify_field(fancy.ack, 0);
  modify_field(fancy.fsm, 0);
  modify_field(meta.counter_update_type_out, COUNTER_RESET);
}

action send_counter_ack() {
  modify_field(fancy.action_value, COUNTER);
  modify_field(fancy.count_flag, 0);
  modify_field(fancy.ack, 1);
  modify_field(fancy.fsm, 0);
  modify_field(meta.counter_update_type_out, COUNTER_RESET);
}

action send_stop() {
  add_header(fancy);
  modify_field(fancy.id, meta.packet_id);
  modify_field(fancy.nextHeader, ethernet.etherType);
  modify_field(ethernet.etherType, FANCY);
  modify_field(fancy.action_value, STOP);
  modify_field(fancy.count_flag, 0);
  modify_field(fancy.ack, 0);
  modify_field(fancy.fsm, 0);
}

action send_stop_already_fancy() {
  //add_header(fancy);
  //modify_field(fancy.nextHeader, ethernet.etherType);
  //modify_field(ethernet.etherType, FANCY);
  modify_field(fancy.action_value, STOP);
  modify_field(fancy.count_flag, 0);
  modify_field(fancy.ack, 0);
  modify_field(fancy.fsm, 0);
}

table egress_port_to_port_id {
    reads { 
      eg_intr_md.egress_port: exact;
    }
    actions {
      set_port_id; //ingress action
      _NoAction;
    }
    default_action: _NoAction();
    size: 32;
}

table table_idle_to_idle_out {
  actions {
    send_counter_ack;
  }
  default_action: send_counter_ack();
}

table table_idle_to_start_ack_out {
  reads {
    fancy.valid: exact;
  }
  actions {
    send_start;
    send_start_already_fancy;
    _NoAction;
  }
  default_action: _NoAction();
  size: 2;
}

table table_start_ack_to_start_ack_out {
  actions {
    send_counter_ack;
  }
  default_action: send_counter_ack();
}

table table_start_ack_to_start_ack_out2 {
  reads {
    fancy.valid: exact;
  }  
  actions {
    send_start;
    send_start_already_fancy;
    _NoAction;
  }
  default_action: _NoAction();
  size: 2;
}

table table_start_ack_to_counting {
  actions {
    drop_exit_egress;
  }
  default_action: drop_exit_egress();
}

table table_counting_to_wait_counter {
  reads {
    fancy.valid: exact;
  }    
  actions {
    send_stop;
    send_stop_already_fancy;
    _NoAction;
  }
  default_action: _NoAction();
  size: 2;
}

table table_wait_counter_to_idle {
  actions {
    send_counter_ack;
  }
  default_action: send_counter_ack();
}

table table_wait_counter_to_start_ack {
  reads {
    fancy.valid: exact;
  }  
  actions {
    send_start;
    send_start_already_fancy;
    _NoAction;
  }
  default_action: _NoAction();
  size: 2;
}

table table_wait_counter_to_wait_counter {
  reads {
    fancy.valid: exact;
  }    
  actions {
    send_stop;
    send_stop_already_fancy;
    _NoAction;
  }
  default_action: _NoAction();
  size: 2;
}

action set_enable_pkt_count() {
  modify_field(fancy.count_flag, 1);
  modify_field(meta.counter_update_type_out, COUNTER_INCREASE);
  //fancy.id =id;
  //fancy.seq = seq;
}

table table_enable_pkt_count {
  actions {
    set_enable_pkt_count;
  }
  default_action: set_enable_pkt_count();
}

action add_fancy_counter_header() {
  add_header(fancy);
  modify_field(fancy.id, meta.packet_id);
  modify_field(fancy.action_value, COUNTER);
  modify_field(fancy.count_flag, 0);
  modify_field(fancy.ack, 0);
  modify_field(fancy.fsm, 1);
  modify_field(fancy.counter_value, meta.local_counter_in);
  /* ethernet stuff */
  modify_field(fancy.nextHeader, ethernet.etherType);
  modify_field(ethernet.etherType, FANCY);
}

table table_add_fancy_counter_header {
  actions {
    add_fancy_counter_header;
  }
  default_action: add_fancy_counter_header();
}

action add_egress_fancy_header() {
  add_header(fancy);
  modify_field(fancy.id, meta.packet_id);
  modify_field(fancy.count_flag, 1);
  modify_field(fancy.ack, 0);
  modify_field(fancy.fsm, 0);
  modify_field(fancy.nextHeader, ethernet.etherType);
  modify_field(fancy.action_value, 0);
  modify_field(ethernet.etherType, FANCY);
  modify_field(meta.counter_update_type_out, COUNTER_INCREASE);

}
table table_egress_add_fancy_header {
  actions {
    add_egress_fancy_header;
  }
  default_action: add_egress_fancy_header();
}

action remove_egress_fancy_header() {
  modify_field(ethernet.etherType, fancy.nextHeader);
  remove_header(fancy);
}

table table_egress_remove_fancy_header {
  actions {
    remove_egress_fancy_header;
  }
  default_action: remove_egress_fancy_header();
}

table egress_drop_duplicate_control_pkts {
  //reads {
  //  meta.entered_as_control: exact;
  //  meta.state_change: exact;
  //  eg_intr_md_from_parser_aux.clone_src: exact;
  //}
  actions {
    drop_exit_egress;
  }
  default_action: drop_exit_egress();
}

action set_debug_mac() {
  modify_field(ethernet.srcAddr, eg_intr_md.egress_port);
}
 
table t_set_debug_mac {
  actions {
    set_debug_mac;
  }
  default_action: set_debug_mac ();
}

table table_drop_control_egress {
  actions { 
    drop_exit_egress;
  }
  default_action: drop_exit_egress();
}

/* Temporal diff thing */
action compute_counter_diff() {
    subtract(fancy.counter_value, meta.local_counter_out, fancy.counter_value);
}

table table_compute_counter_diff {
  actions {
    compute_counter_diff;
  }
  default_action: compute_counter_diff();
}

/* debug */

action increase_ip_id() {
  add_to_field(ipv4.identification, 1);
  //modify_field(eg_intr_md_for_oport.drop_ctl, 1);
}

table table_increase_ip_id {
  actions {
    increase_ip_id;
  }
  default_action: increase_ip_id();
}

/* Field list definitions */
field_list set_reroute_fields {
  meta.is_internal;
  meta.control_type;
  meta.packet_id; 
  meta.original_port;
}

action _clone_to_recirculation(mirror_id){
  modify_field(meta.is_internal, 1);
  modify_field(meta.control_type, REROUTE_RECIRCULATE);
  modify_field(meta.original_port, eg_intr_md.egress_port);
  // meta.packet_id; ?
  clone_egress_pkt_to_egress(mirror_id, set_reroute_fields);
}

table clone_to_recirculation {
  reads {
      eg_intr_md.egress_port mask 0x180: exact;    
  }
  actions {
    _clone_to_recirculation;
  }
  default_action: _clone_to_recirculation(101); // pipe 0 -> 100, pipe 1 -> 101
  size: 4;
}

/* sets the fields properly*/
action add_fancy_pre_header()
{ 
  add_header(fancy_pre);
  modify_field(ethernet.etherType, FANCY_PRE);
  modify_field(fancy_pre.set_bloom, 1);
  modify_field(fancy_pre.port, meta.original_port);
  modify_field(fancy_pre.hash_0, meta.packet_id);
}

table table_add_fancy_pre_header{
  actions {
    add_fancy_pre_header;
  }
  default_action: add_fancy_pre_header ();
  size : 1;
}

/*EGRESSS PIPE*/
control egress_ctrl {

  /* For Debug Purposes: Set source mac address to: 00:00:00:00:00: port */
  // Not strictly needed, used to make debugging easier, but can be removed. 
  apply(t_set_debug_mac);

  /* Egress State Machine: Represents the sending side */
  apply(egress_fancy_enabled);

  /* Obtain addressing properties for this packet */
  apply(egress_port_to_port_id);
  
  /* Comes from the other switch */
  if (meta.is_internal == 0)
  {
    if (meta.egress_type == SWITCH)
    { 
      /* Addressing */
      /* We need to get the memory index for this packet SM */
      if (not valid(fancy))
      {
        /* computes the address using meta.packet_id */
        apply(egress_compute_addresses_no_fancy);
      }
      else {
        /* Computes the address using fancy.id */
        /* This is needed for only control plane packets since they dont
          have IP maybe */
        apply(egress_compute_addresses_fancy);
      }    

      /* Stage 0 */
      /* Read and update state */
      apply(table_read_update_state_out);
      apply(table_update_counter_out);

      /* Stage 1 */
      /* Compute next state */
      if (meta.control_type == 0)
      {
        apply(table_next_state_out) {
          miss {
            // If its a control packet and did not hit the table we drop it
            if (meta.entered_as_control == 1)
            {
              apply(table_drop_control_egress);
            }
          }
        }
      }

      /* Stage 2 */
      /* Lock state or check if state is locked */
      apply(table_state_lock_out);
      
      /* Stage 3*/
      /* If state was locked now, we resubmit and clone (if needed we drop) */  
      if (meta.lock_status == LOCK_OBTAINED)
      {
        apply(table_mirror_to_update);
      }
      /* when the packet has looped to release the lock */
      else if (meta.lock_status ==  LOCK_RELEASED)
      {
        /* State Change Logic */
        if (meta.prev_state == SENDER_IDLE and meta.next_state == SENDER_IDLE)
        { 
          apply(table_idle_to_idle_out);
        }
        else if (meta.prev_state == SENDER_IDLE and meta.next_state == SENDER_START_ACK)
        {
          apply(table_idle_to_start_ack_out);        
        }
        /* This can happen when the receiver sends us a very late counter, we just ACK it, and reset all again */
        /* The transition below is the one that does the rentransmission when the START ACK never arrived */
        else if (meta.prev_state == SENDER_START_ACK and meta.next_state == SENDER_START_ACK and meta.state_change_counter == 0)
        {
          /* Sends COUNTER ACK eventough the nameing might be confusing */
          apply(table_start_ack_to_start_ack_out);        
        }
        /* This one means that this is a transition made by a counterr reaching some value, i guess this is to send a retransmission */
        /* plus is a way to differenciate with the previous transition which has tne same src dst states*/
        else if (meta.prev_state == SENDER_START_ACK and meta.next_state == SENDER_START_ACK and meta.state_change_counter == 1)
        {
          apply(table_start_ack_to_start_ack_out2);        
        }

        else if (meta.prev_state == SENDER_START_ACK and meta.next_state == SENDER_COUNTING)
        {
          apply(table_start_ack_to_counting);        
        }
        else if (meta.prev_state == SENDER_COUNTING and meta.next_state == SENDER_WAIT_COUNTER_RECEIVE)
        {
          apply(table_counting_to_wait_counter);        
        }

        /* HERE IS WHERE WE WOULD MOVE TO A COMPUTE STATE INSTEAD */
        else if (meta.prev_state == SENDER_WAIT_COUNTER_RECEIVE and meta.next_state == SENDER_IDLE)
        {
                   apply(table_wait_counter_to_idle);        
        }
        else if (meta.prev_state == SENDER_WAIT_COUNTER_RECEIVE and meta.next_state == SENDER_START_ACK)
        {
          apply(table_wait_counter_to_start_ack);        
        }
        /**********************************************************/
        else if (meta.prev_state == SENDER_WAIT_COUNTER_RECEIVE and meta.next_state == SENDER_WAIT_COUNTER_RECEIVE)
        {
          apply(table_wait_counter_to_wait_counter);        
        }
      }
    }

    /* END OF EGRESS LOGIC */
    
    /* This is done to drop the original control packet. When a state update is needed a e2e clone is performed to update the state however
       the original control packet is not needed anymore
    */
    if (meta.entered_as_control == 1 and eg_intr_md_from_parser_aux.clone_src == NOT_CLONED and meta.state_change == 1)
    {
      apply(egress_drop_duplicate_control_pkts);     
    }

    /* I am sure this needs more flags to be checked, for example cloned packets will have to be treated in some special way */
    /* Need to make sure that only packets that will leave the switch enter here... CHECKING THE LOCK IS NOT IMPORTANT BUT....*/
    /* and meta.lock_status != LOCK_NONE : this is removed because normal packets also see the lock blocked*/
    /* This makes the thing count some extra packets while the state is being updated */
    else if (meta.egress_type == SWITCH and meta.current_state == SENDER_COUNTING and valid(ipv4))
    {
      if (valid(fancy))
      {
        apply(table_enable_pkt_count);
      }
      /* this also adds a flag*/
      else 
      {
        apply(table_egress_add_fancy_header);
      }
    }
    else if ((meta.egress_type != SWITCH) and (valid(fancy)))
    {
      /* remove the header, and restore ethernet protocol */
      apply(table_egress_remove_fancy_header);
    }

    /*COUNT PACKET */
    /* Count for this packet */
    /* Or reset, depending on the packet transition in the state machine */
    /* also reads the coubter */
    apply(table_packet_count_out);

    /* Here we do the counter difference logic, before reporting the counter */
    /* we do this here because before we did not have the counter value */
    if (meta.lock_status ==  LOCK_RELEASED and (meta.prev_state == SENDER_WAIT_COUNTER_RECEIVE and (meta.next_state == SENDER_IDLE or meta.next_state == SENDER_START_ACK)))
    {
      /* Counter difference */
      /* We set the counter diff to fancy.counter_value in the ACK message just for debugging */
      apply(table_compute_counter_diff);

      // if fancy.counter_value != 0 we report this to the ingress to do that 
      // we use e2e clone and we clone to recirc port
      #ifdef REROUTE
      if (fancy.counter_value != 0)
      {
        apply(clone_to_recirculation);
      }
      #endif
      
    }
  }
  
  /* Special cloned packets from the ingress for which we need to add a FANCY header and some data */
  /* We need to do this when we need to generate a control packet from normal traffic */
  else if (meta.is_internal == 1 and meta.control_type == INGRESS_SEND_COUNTER and eg_intr_md_from_parser_aux.clone_src == CLONED_FROM_INGRESS)
  {
    apply(table_add_fancy_counter_header);
  }

  /* re route recirculated packet to send to ingress */
  #ifdef REROUTE
  else if (meta.is_internal == 1 and meta.control_type == REROUTE_RECIRCULATE and eg_intr_md_from_parser_aux.clone_src == CLONED_FROM_EGRESS)
  {
    apply(table_add_fancy_pre_header);
  }
  #endif

  /* Increase IP indentification for debugging purposes*/
  //apply(table_increase_ip_id);    
}