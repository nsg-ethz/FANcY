

/*** INGRESS PIPELINE ***/

/* drop 3-bit field:

[2]-> disable mirroring
[1]-> disable copy_to_cpu
[0]-> disable unicast, multicast or resubmit
*/

action drop_exit_ingress() {
  modify_field(ig_intr_md_for_tm.drop_ctl, 1);
  exit();
}

action drop_ingress() {
  modify_field(ig_intr_md_for_tm.drop_ctl, 1);
}

action strong_drop_ingress() {
  modify_field(ig_intr_md_for_tm.drop_ctl, 7);
}

/* Register Definition */

/* This is the counter used for state transition */
register counters_in {
    width : 32;
    instance_count : NB_REGISTER_SIZE;
}

/* This is the counter used for packet counts*/
register pkt_counters_in {
    width : 32;
    instance_count : NB_REGISTER_SIZE;
}

register state_in {
    width : 8;
    instance_count : NB_REGISTER_SIZE;
}

register state_lock_in {
    width : 8;
    instance_count : NB_REGISTER_SIZE;
}

register reroute_register {
    width: 1;
    instance_count: NB_REGISTER_SIZE;
}

/* Field list definitions */
field_list state_update_fields {
  meta.prev_state;
  meta.next_state;
  meta.state_change;
  /* if this meta is not copied, some control message retrans missions 
     stop working. Specifically egress trans : apply(table_start_ack_to_start_ack_out2);    
     however, it does not compile with 8.9.2 */
  #ifdef SDE9
  meta.state_change_counter; 
  #endif
  meta.control_type;
  meta.packet_id; // we keep the packet id
  //meta.entered_as_control;   /* not really needed but i want to keep it */
}

/* Fields needed when a clone is generated from normal traffic */
field_list send_counter_i2e_fields {
  meta.is_internal;
  meta.control_type;
  meta.local_counter_in;
  meta.packet_id;
}

/* Stateful alus logic */

/* Stage 0 state change*/
blackbox stateful_alu read_update_state_in {
    reg     : state_in;

    condition_lo: meta.control_type == STATE_UPDATE_INGRESS;

    update_lo_1_predicate: not condition_lo;
    update_lo_1_value: register_lo;

    update_lo_2_predicate: condition_lo;
    update_lo_2_value: meta.next_state;

    output_value    :   alu_lo;
    output_dst      :   meta.current_state;
}

/* stage 0 counter change*/
blackbox stateful_alu update_counter_in {
    reg     : counters_in;

    condition_lo: meta.control_type == STATE_UPDATE_INGRESS;

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
blackbox stateful_alu read_update_state_lock_in {
    reg     : state_lock_in;

    condition_lo: meta.control_type == STATE_UPDATE_INGRESS;
    /* register lo can be either 0 or 10 thus, if 1  state_change=1 */
    condition_hi: register_lo + meta.state_change == 1; 

    update_lo_1_predicate: condition_lo and not condition_hi;
    update_lo_1_value: 0;

    update_lo_2_predicate: condition_hi and not condition_lo;
    update_lo_2_value: LOCK_VALUE;

    output_value    :   predicate;
    output_dst      :   meta.lock_status;
}

/* Ingress Packet counter */
blackbox stateful_alu increase_pkt_counters_in {
    reg     : pkt_counters_in;

    condition_lo: meta.counter_update_type_in == COUNTER_INCREASE;
    condition_hi: meta.counter_update_type_in == COUNTER_RESET;
    
    update_lo_1_predicate: condition_lo;
    update_lo_1_value: register_lo + 1;

    update_lo_2_predicate: condition_hi;
    update_lo_2_value: 0;

    // outputing register_lo is a way of getting the previous value
    output_value    :   register_lo;
    output_dst      :   meta.local_counter_in;
}

action action_packet_count_in() {
  increase_pkt_counters_in.execute_stateful_alu(meta.dedicated_address);
}

table table_packet_count_in {
  actions {
    action_packet_count_in;
  }
  default_action: action_packet_count_in();
}

/* Ingress Actions  and tables */
action set_port(outport)
{
    modify_field(ig_intr_md_for_tm.ucast_egress_port, outport);
}

table forward {
  reads { 
    ig_intr_md.ingress_port: exact;
  }
  actions {
    set_port;
    _NoAction;
  }
  default_action: _NoAction();
}

action compute_addresses_no_fancy()
{
  add(meta.dedicated_address, meta.port_address_offset, meta.packet_id);
}

table ingress_compute_addresses_no_fancy {
  actions {
    compute_addresses_no_fancy;
  }
  default_action: compute_addresses_no_fancy();
  size: 1;
}

action compute_addresses_fancy()
{
  add(meta.dedicated_address, meta.port_address_offset, fancy.id);
}

table ingress_compute_addresses_fancy {
  actions {
    compute_addresses_fancy;
  }
  default_action: compute_addresses_fancy();
  size: 1;
}

action set_port_id(address_offset)
{
  modify_field(meta.port_address_offset, address_offset);
}

table ingress_port_to_port_id {
    reads { 
      ig_intr_md.ingress_port: exact;
    }
    actions {
      set_port_id;
      _NoAction;
    }
    default_action: _NoAction();
    size: 32;
}

/* REROUTE LOGIC */
/* to make it simple lets reroute by entire port */
table reroute {
  reads { 
    ig_intr_md_for_tm.ucast_egress_port: exact;
  }
  actions {
    set_port;
    _NoAction;
  }
  default_action: _NoAction();
}

blackbox stateful_alu reroute_register_set {
    reg: reroute_register;

    update_lo_1_value: set_bit;
    output_value: alu_lo;
    output_dst: meta.reroute;
}

blackbox stateful_alu reroute_register_read {
    reg: reroute_register;

    update_lo_1_value: read_bit;
    output_value: alu_lo;
    output_dst: meta.reroute;
}

action _read_reroute_register()
{
    reroute_register_read.execute_stateful_alu(meta.reroute_address);
}

table read_reroute_register {
    actions {
        _read_reroute_register;
    }
    default_action: _read_reroute_register ();
    size: 1;
}

action _set_reroute_register()
{
    reroute_register_set.execute_stateful_alu(meta.reroute_address);
    drop_exit_ingress();
}

#ifdef SDE8
@pragma stage 2
#endif
table set_reroute_register {
    actions {
        _set_reroute_register;
    }
    default_action: _set_reroute_register ();
    size: 1;
}

/* used for the reroute addressing */
action set_reroute_address_read(address_offset)
{
  add(meta.reroute_address, address_offset, meta.packet_id);
}

table port_to_reroute_address_read {
    reads { 
      ig_intr_md_for_tm.ucast_egress_port: exact;
    }
    actions {
      set_reroute_address_read;
      _NoAction;
    }
    default_action: _NoAction();
    size: 32;
}

/* used for the reroute addressing */
action set_reroute_address_set(address_offset)
{
  // hash 0 carries the prefix id
  add(meta.reroute_address, address_offset, fancy_pre.hash_0);
}

table port_to_reroute_address_set {
    reads { 
      fancy_pre.port: exact;
    }
    actions {
      set_reroute_address_set;
      _NoAction;
    }
    default_action: _NoAction();
    size: 32;
}

/* we set the dedicated entry id */
action set_packet_id(packet_id)
{
  modify_field(meta.packet_id, packet_id);
}

table packet_to_id {
    reads { 
      ipv4.dstAddr: exact;
    }
    actions {
      set_packet_id;
      _NoAction;
    }
    default_action: set_packet_id(ENTRY_ZOOM_ID); /* default to tree*/
    size: NUM_DEDICATED_ENTRIES;
}


action set_ingress_type(ingress_type) {
  modify_field(meta.ingress_type, ingress_type);
}

table ingress_fancy_enabled {
  reads {
    ig_intr_md.ingress_port: exact;
  }
  actions {
    set_ingress_type;
    _NoAction;
  }
  default_action: _NoAction();
  size: 64;
}

action action_read_update_state_in()
{
  read_update_state_in.execute_stateful_alu(meta.dedicated_address);
}

table table_read_update_state_in
{
  actions {
    action_read_update_state_in;
  }
  default_action: action_read_update_state_in();
}

action action_update_counter_in()
{
  update_counter_in.execute_stateful_alu(meta.dedicated_address);
}

table table_update_counter_in
{
  actions {
    action_update_counter_in;
  }
  default_action: action_update_counter_in();
}

action set_next_state_in(next_state, counter_type)
{
  modify_field(meta.next_state, next_state);
  modify_field(meta.prev_state, meta.current_state);
  modify_field(meta.state_change, 1);
  modify_field(meta.state_change_counter, counter_type);
}

table table_next_state_in
{
  reads{
    meta.current_state: exact;
    meta.current_counter: ternary;
    fancy.action_value: ternary;
    fancy.ack: ternary;
    fancy.valid: ternary;
  }
  actions {
    set_next_state_in;
    _NoAction;
  }
  default_action: _NoAction();
}

action action_state_lock_in()
{
  read_update_state_lock_in.execute_stateful_alu(meta.dedicated_address);
}

table table_state_lock_in
{
  actions {
    action_state_lock_in;
  }
  default_action: action_state_lock_in();
}

action action_resubmit_to_update() {
  modify_field(meta.control_type, STATE_UPDATE_INGRESS);
  resubmit(state_update_fields);
}

table table_resubmit_to_update {
  actions {
    action_resubmit_to_update;
  }
  default_action: action_resubmit_to_update();
}

/* STATE CHANGE TABLES */

action send_start_ack() {
  modify_field(fancy.action_value, START);
  modify_field(fancy.count_flag, 0);
  modify_field(fancy.ack, 1);
  modify_field(fancy.fsm, 1);
  modify_field(meta.is_internal, 1);
  modify_field(ig_intr_md_for_tm.ucast_egress_port, ig_intr_md.ingress_port);
}

table table_idle_to_counting_in {
  actions {
    send_start_ack;
  }
  default_action: send_start_ack();
}

table table_counting_to_counting_in {
  actions {
    send_start_ack;
  }
  default_action: send_start_ack();
}

table table_counter_ack_counting_in {
  actions {
    send_start_ack;
  }
  default_action: send_start_ack();
}

action send_counter() {
  modify_field(fancy.action_value, COUNTER);
  modify_field(fancy.count_flag, 0);
  modify_field(fancy.ack, 0);
  modify_field(fancy.fsm, 1);
  modify_field(fancy.counter_value, meta.local_counter_in);
  modify_field(meta.is_internal, 1);
  modify_field(ig_intr_md_for_tm.ucast_egress_port, ig_intr_md.ingress_port);
}

table table_counter_send_to_counter_ack_in {
  actions {
    send_counter;
  }
  default_action: send_counter();
}

table table_counting_to_counter_ack_in {
  actions {
    send_counter;
  }
  default_action: send_counter();
}

/* Since sending this counter could be triggered by normal traffic we need 
   to leave the packet unmodified at the ingress and then add stuff
   at the egress using a i2e clone 
*/
action send_counter_i2e(mirror_id) {
  modify_field(meta.is_internal, 1);
  modify_field(meta.control_type, INGRESS_SEND_COUNTER);
  clone_ingress_pkt_to_egress(mirror_id, send_counter_i2e_fields);
}

table table_counter_send_to_counter_ack_i2e_in {
  reads {
    ig_intr_md.ingress_port: exact;
  }
  actions {
    send_counter_i2e;
  }
  default_action: send_counter_i2e(511);
  size: 64;
}

table table_counter_ack_to_counter_ack_i2e_in {
  reads {
    ig_intr_md.ingress_port: exact;
  }  
  actions {
    send_counter_i2e;
  }
  default_action: send_counter_i2e(511);
  size: 64;

}

table table_counter_ack_to_counter_ack_in {
  actions {
    send_counter;
  }
  default_action: send_counter();
}

table table_counting_to_wait_counter_send {
  actions {
    drop_exit_ingress;
  }
  default_action: drop_exit_ingress();
}

table table_counter_ack_to_idle {
  actions {
    drop_exit_ingress;
  }
  default_action: drop_exit_ingress();
}

action set_control_flag() {
  modify_field(meta.entered_as_control, 1);
}

table table_set_control_flag {
  actions {
    set_control_flag;
  }
  default_action: set_control_flag();
}

action set_egress_as_ingress() {
  modify_field(ig_intr_md_for_tm.ucast_egress_port, ig_intr_md.ingress_port);
  exit(); 
}

table table_ingress_to_egress {
  actions {
    set_egress_as_ingress;
  }
  default_action: set_egress_as_ingress();
}

table table_drop_control_ingress {
  actions {
    drop_exit_ingress;
  }
  default_action: drop_exit_ingress();
}

action set_increase_counter_update_type_in() {
  modify_field(meta.counter_update_type_in, COUNTER_INCREASE);
}

action set_reset_counter_update_type_in() {
  modify_field(meta.counter_update_type_in, COUNTER_RESET);
}

table table_set_increase_counter_update_type_in {
  actions {
    set_increase_counter_update_type_in;
  }
  default_action: set_increase_counter_update_type_in ();
}

table table_set_reset_counter_update_type_in {
  actions {
    set_reset_counter_update_type_in;
  }
  default_action: set_reset_counter_update_type_in ();
}

table first_drop {
  actions {
    drop_exit_ingress;
  }
  default_action: drop_exit_ingress ();
}



/*INGRESS PIPE*/
control ingress_ctrl {
    /* We drop all LLDP packets*/
    if (ethernet.etherType == LLDP)
    {
      apply(first_drop);
    }
  
    /* Decide if this packet is not a control packet */
    /* When it arrives */
    /* this also affects resubmissions */

    if (valid(fancy) and (fancy.action_value != KEEP_ALIVE))
    {
      apply(table_set_control_flag);
    }

    /* unconditional forwarding. Should I remove this for control? */
    apply(forward);

    /* Obtain addressing properties for this packet */
    apply(ingress_port_to_port_id);

    /* Get packet ID */
    /* If its a dedicated counter entry we get a number from 0 to 510, otherwise 511 for the tree? */
    apply(packet_to_id);

    /* Check ingress type */
    apply(ingress_fancy_enabled);

    #ifdef REROUTE
    /* Reroute logic */
    /* Get output port addressing outport offset + prefix id */
    if (valid(fancy_pre) and fancy_pre.set_bloom == 1)
    {
      /* get addressing uses the fancy_pre port */
      apply(port_to_reroute_address_set);

      /* sets reroute bit  */
      apply(set_reroute_register);
    }

    /* normal packets and not from the others */
    else if (valid(ipv4) and meta.packet_id != ENTRY_ZOOM_ID)
    {
      /* get addressing using current output port */
      apply(port_to_reroute_address_read);

      /* access reroute register*/
      apply(read_reroute_register);
      
      /* reroute table */
      if (meta.reroute == 1)
      {
        apply(reroute);
      }
    }
    #endif

    if (meta.ingress_type == SWITCH)
    {
      /* For now we wont use them to count, it could get messy if we do */
      /* this is directly sent to the egress */
      if (meta.entered_as_control == 1 and fancy.fsm == 1)
      {
        /* This packet is destined to the egress FMS, we set egress<-ingress */
        apply(table_ingress_to_egress);
      }
      /* Rest of packets: Ingress state machine */
      else 
      {
        /* We need to get the memory index for this packet SM */
        if (not valid(fancy))
        {
          /* computes the address using meta.packet_id */
          apply(ingress_compute_addresses_no_fancy);
        }
        else {
          /* Computes the address using fancy.id */
          /* This is needed for only control plane packets since they dont
           have IP maybe */
          apply(ingress_compute_addresses_fancy);
        }        

        /* Stage 0 */
        /* Read and update state */
        apply(table_read_update_state_in);
        apply(table_update_counter_in);

        /* Ingress Count packets: read & update & reset */
        /*************************************************************/
        if (meta.current_state == RECEIVER_COUNTING and fancy.count_flag == 1)
        {
          /* set flag to increase */
          apply(table_set_increase_counter_update_type_in);
        }
        /* TODO: also check if the start matches in the state transition table. This could be an attack vector. This can be used to reset the counter all the time right?*/
        else if (fancy.action_value == START)
        {
          /* set flag to reset */ 
          apply(table_set_reset_counter_update_type_in);
        }
        /* if no flag set we should just read it*/
        /* The flags are set in the two previous conditions */
        apply(table_packet_count_in);
        /*************************************************************/


        /* Stage 1 */
        /* Compute next state */
        /* If control type is not 0 we dont check this */
        if (meta.control_type == 0)
        {
          apply(table_next_state_in) {
            miss {
              /* If its a control packet and did not hit the table we drop it  inmediately */
              /* control packets that do not hit, they got lost maybe? */
              if (meta.entered_as_control == 1)
              {
                apply(table_drop_control_ingress);
              }
            }
          }
        }

        /* Stage 2 */
        /* Lock state or check if state is locked */
        apply(table_state_lock_in);
        
        /* Stage 3*/
        /* If state was locked now, we resubmit */
        if (meta.lock_status == LOCK_OBTAINED)
        {
          apply(table_resubmit_to_update);
        }
        else if (meta.lock_status ==  LOCK_RELEASED)
        {
          /* State Change Logic */
          if (meta.prev_state == RECEIVER_IDLE and meta.next_state == RECEIVER_COUNTING)
          { 
            /* 
              1. Reset counting counter
              2. Set received SEQ number
            */
            apply(table_idle_to_counting_in);

          }
          else if (meta.prev_state == RECEIVER_COUNTING and meta.next_state == RECEIVER_COUNTING)
          {
            /* 
              1. Reset counting counter
              2. Set received SEQ number
            */
            apply(table_counting_to_counting_in);        
          }
          //else if (meta.prev_state == RECEIVER_COUNTING and meta.next_state == RECEIVER_WAIT_COUNTER_SEND)
          //{
          //  /* just drops the packet */
          //  apply(table_counting_to_wait_counter_send);
          //}
          // We replaced the transition above by this one!
          // new state from counting to counter ack -> thus we send counter already
          else if (meta.prev_state == RECEIVER_COUNTING and meta.next_state == RECEIVER_COUNTER_ACK)
          {
            /* just drops the packet */
            apply(table_counting_to_counter_ack_in);
          }
          /* Due to the change above we managed to also remove this complex state transition */
          /* This transition is super complex pay attention*/
          /* If the sending of a counter is triggered by normal packets we need a i2e cloning*/
          /* Otherwise we use the control packet itself*/
          //else if (meta.prev_state == RECEIVER_WAIT_COUNTER_SEND and meta.next_state == RECEIVER_COUNTER_ACK)
          //{
          //  /* sends counter */
          //  /* Special transition that needs to be done differently if the packet is a control or normal traffic */
          //  if (meta.entered_as_control == 1)
          //  {
          //    apply(table_counter_send_to_counter_ack_in);
          //  }
          //  else 
          //  {
          //    /* Clone packet i2e and, one if normally forwarded, the other is used to reply */
          //    apply(table_counter_send_to_counter_ack_i2e_in);
          //  }
          //}
          
          /* this can happen because of two different things: stop or counter expires */
          /* Special transition that needs to be done differently if the packet is a control or normal traffic */
          /* Same than above */
          else if (meta.prev_state == RECEIVER_COUNTER_ACK and meta.next_state == RECEIVER_COUNTER_ACK)
          {
            /* sends counter */
            if (meta.entered_as_control == 1)
            {
              apply(table_counter_ack_to_counter_ack_in);
            }
            else 
            {
              /* Clone packet i2e and, one if normally forwarded, the other is used to reply */
              apply(table_counter_ack_to_counter_ack_i2e_in);
            }
            
          }
          else if (meta.prev_state == RECEIVER_COUNTER_ACK and meta.next_state == RECEIVER_IDLE)
          {
            apply(table_counter_ack_to_idle);
          }
          else if (meta.prev_state == RECEIVER_COUNTER_ACK and meta.next_state == RECEIVER_COUNTING)
          {
            apply(table_counter_ack_counting_in);
          }
        }

      }
    }    
}