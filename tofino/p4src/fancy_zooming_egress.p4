header_type egress_meta_t {
    fields {
        count_packet_flag: 1;
        max_0: 16;
        max_1: 16;
        zooming_stage: 8;
        state: 8;
        simple_address: 8;
        counter_address: 16;
        local_counter_and_diff: 32 (saturating);
        counter_diff_excess: 32 (saturating);
    }
}

action _build_egr_hash_path(){
  modify_field(fancy_pre.hash_0, egr_meta.max_0);
  modify_field(fancy_pre.hash_1, egr_meta.max_1);
  // i could save 16 bit by actually not even copying this since it comes
  modify_field(fancy_pre.hash_2, fancy_counters_length._length); 

  //set bloom
  modify_field(fancy_pre.set_bloom, 1);
}

table build_egr_hash_path {
  actions {
    _build_egr_hash_path;
  }
  default_action: _build_egr_hash_path();
  size: 1;
}

register zooming_stage {
    width : 8;
    instance_count : 32;
}

register out_state {
    width : 8;
    instance_count : 32;
}

// We do them 32 bit wide since we allocate both the max diff and the max
// index in the same register, this could be memory optimized at the price
// of one stage 
register max_0 {
    width : 16;
    instance_count : 32;
}

register max_1 {
    width : 16;
    instance_count : 32;
}

register out_counters {
    width : 32;
    instance_count : 1024;
    //attributes : saturating; NOT NEEDED ANYMORE
}


action set_egress_address_offsets_normal(counter_offset, simple_offset) {
    // we set the base only
    modify_field(egr_meta.counter_address, counter_offset); 
    modify_field(egr_meta.simple_address, simple_offset);
}

// This could actually be optimized if we make the assumption that ingress and
// egress port of this type of packets should be the same, if we need space, this can be done differently
action set_egress_address_offsets_recirc(counter_offset, simple_offset) {
    // base + length
    add(egr_meta.counter_address, counter_offset, fancy_counters_length._length); 
    modify_field(egr_meta.simple_address, simple_offset);
}

table out_port_to_offsets {
    reads {
        fancy_pre.valid: exact;
        eg_intr_md.egress_port: ternary;
        fancy_pre.port: ternary;
    }
    actions {
        set_egress_address_offsets_normal;
        set_egress_address_offsets_recirc;
        _NoAction;
    }
    default_action: _NoAction ();
    size: 32;
}

// crc_8, crc_8_darc crc_8_i_code crc_8_itu
blackbox stateful_alu read_update_zooming_stage {
    reg     : zooming_stage;

    condition_lo: fancy_pre.pre_type >= UPDATE_OFFSET; // the offset we set for this update
    condition_hi: register_lo == MAX_ZOOM; //2

    update_lo_1_predicate: condition_lo and not condition_hi;
    update_lo_1_value: register_lo + 1;

    update_lo_2_predicate: condition_lo and condition_hi;
    update_lo_2_value: 0;

    output_value    :   register_lo; //  not sure its lo or alu
    output_dst      :   egr_meta.zooming_stage;
}

action do_update_read_zooming_stage()
{
   read_update_zooming_stage.execute_stateful_alu(egr_meta.simple_address);
}


table read_update_zooming_stage {
  actions {
    do_update_read_zooming_stage;
  }
  default_action: do_update_read_zooming_stage();
  size: 1;  
}


blackbox stateful_alu read_update_max_0 {
    reg     : max_0;

    condition_lo: fancy_pre.pre_type == UPDATE_MAX_0;
    
    update_lo_1_predicate: condition_lo;
    update_lo_1_value: fancy_pre.max_index;

    update_lo_2_predicate: not condition_lo;// and condition_hi;
    update_lo_2_value: register_lo;

    output_value    :   alu_lo;
    output_dst      :   egr_meta.max_0; 
}

action _read_update_max_0()
{
   read_update_max_0.execute_stateful_alu(egr_meta.simple_address);
}


table read_update_max_0 {
  actions {
    _read_update_max_0;
  }
  default_action: _read_update_max_0();
  size: 1;  
}

blackbox stateful_alu read_update_max_1 {
    reg     : max_1;

    condition_lo: fancy_pre.pre_type == UPDATE_MAX_1;
    
    update_lo_1_predicate: condition_lo;
    update_lo_1_value: fancy_pre.max_index;

    update_lo_2_predicate: not condition_lo;// and condition_hi;
    update_lo_2_value: register_lo;

    output_value    :   alu_lo;
    output_dst      :   egr_meta.max_1;
}

action _read_update_max_1()
{
   read_update_max_1.execute_stateful_alu(egr_meta.simple_address);
}

table read_update_max_1 {
  actions {
    _read_update_max_1;
  }
  default_action: _read_update_max_1();
  size: 1; 
}

#ifdef HARDWARE
blackbox stateful_alu read_out_state {
    reg     : out_state;

    condition_lo: fancy.action_value == STOP; /* when we forward the STOP event to the other side */
    condition_hi: fancy_pre.pre_type >= UPDATE_OFFSET; /* last loop of counter exchange*/

    update_lo_1_predicate: condition_lo and not condition_hi;
    update_lo_1_value: SENDER_IDLE;

    update_lo_2_predicate: condition_hi and not condition_lo;
    update_lo_2_value: SENDER_COUNTING;

    output_value    :   register_lo;
    output_dst      :   egr_meta.state;
}
#else
blackbox stateful_alu read_out_state {
    reg     : out_state;

    output_value    :   register_lo;
    output_dst      :   egr_meta.state;
}
#endif

action _read_out_state()
{
    read_out_state.execute_stateful_alu(egr_meta.simple_address);
}

table read_out_state {
   actions {
      _read_out_state;
    }
    default_action: _read_out_state ();
    size: 1;
}

blackbox stateful_alu read_reset_counter {
    reg     : out_counters;

    update_lo_1_value: 0;

    output_value    :   register_lo;
    output_dst      :   egr_meta.local_counter_and_diff;
}

action _read_reset_counter(){
    read_reset_counter.execute_stateful_alu(egr_meta.counter_address); 
}

#ifdef SDE9
@pragma stage 3
#endif
#ifdef SDE8
@pragma stage 4
#endif
table table_read_reset_counter {
  actions {
    _read_reset_counter;
  }
  default_action: _read_reset_counter ();
  size: 1;
}

action _subtract_counters()
{
    subtract_from_field(egr_meta.local_counter_and_diff, fancy_counter.counter_value);
    remove_header(fancy_counter);
}

table subtract_counters {
    actions {
        _subtract_counters;
    }
    default_action: _subtract_counters();
    size: 1;
}


action _subtract_differences(){
    subtract(egr_meta.counter_diff_excess, fancy_pre.max_counter_diff, egr_meta.local_counter_and_diff);
}

table subtract_differences{
    actions {
        _subtract_differences;
    }
    default_action: _subtract_differences ();
    size: 1;
}

action _update_max_values()
{
    modify_field(fancy_pre.max_index, fancy_counters_length._length);
    modify_field(fancy_pre.max_counter_diff, egr_meta.local_counter_and_diff);
}

table update_max_values {
    actions {
        _update_max_values;
    }
    default_action: _update_max_values ();
    size: 1;
}

action drop_exit_egress() {
  modify_field(eg_intr_md_for_oport.drop_ctl, 1);
  exit();
}


table drop_egress {
  actions {
    drop_exit_egress;
  }
  default_action: drop_exit_egress ();
  size: 1;
}

action do_set_zoom_address_0()
{
  modify_field(fancy.seq, br_meta.hash_0);
  add_to_field(egr_meta.counter_address, br_meta.hash_0);
  modify_field(egr_meta.count_packet_flag, 1);
}

table set_zoom_address_0 {
  actions {
    do_set_zoom_address_0;
  }
  default_action: do_set_zoom_address_0();
  size: 1;
}

action do_set_zoom_address_1()
{
  modify_field(fancy.seq, br_meta.hash_1);
  add_to_field(egr_meta.counter_address, br_meta.hash_1);
  modify_field(egr_meta.count_packet_flag, 1);
}

table set_zoom_address_1 {
  actions {
    do_set_zoom_address_1;
  }
  default_action: do_set_zoom_address_1();
  size: 1;
}

action do_set_zoom_address_2()
{
  modify_field(fancy.seq, br_meta.hash_2);
  add_to_field(egr_meta.counter_address, br_meta.hash_2);
  modify_field(egr_meta.count_packet_flag, 1);
}

table set_zoom_address_2 {
  actions {
    do_set_zoom_address_2;
  }
  default_action: do_set_zoom_address_2();
  size: 1;
}

blackbox stateful_alu array_modify {
    reg     : out_counters;
    update_lo_1_value: register_lo + 1;
}

action do_add_to_array(){
  //TEST
   array_modify.execute_stateful_alu(egr_meta.counter_address);
}

#ifdef SDE9
@pragma stage 3
#endif
#ifdef SDE8
@pragma stage 4
#endif
table add_to_array {
  actions {
    do_add_to_array;
  }
  default_action: do_add_to_array();
  size: 1;
}

action _set_fancy_pre_type(_type)
{
    modify_field(fancy_pre.pre_type, _type);
}

table set_fancy_pre_type_to_update {
  reads {
      fancy_counters_length._length: exact;
      egr_meta.zooming_stage: exact;
  }
  actions {
    _set_fancy_pre_type;
    _NoAction;
  }
  default_action: _NoAction;
  size: 8;
}

action _add_fancy_counting_header(){
  add_header(fancy);
  //modify_field(fancy.id, meta.seq);
  modify_field(fancy.count_flag, 1);
  modify_field(fancy.ack, 0);
  modify_field(fancy.fsm, 0);
  modify_field(fancy.nextHeader, ethernet.etherType);
  modify_field(fancy.action_value, 0);
  modify_field(ethernet.etherType, FANCY);
}

table add_fancy_counting_header{
    actions {
        _add_fancy_counting_header;
    }
    default_action: _add_fancy_counting_header ();
    size: 1;
}

action _remove_fancy_header(){
    modify_field(ethernet.etherType, fancy.nextHeader);
    remove_header(fancy);
}

table remove_fancy_header {
    actions {
        _remove_fancy_header;
    }
    default_action: _remove_fancy_header();
    size: 1;
}

table remove_fancy_header2 {
    actions {
        _remove_fancy_header;
    }
    default_action: _remove_fancy_header();
    size: 1;
}

/*** EGRESS PIPELINE ***/
control egress_ctrl{

  // IMPORTANT: WE CAN MERGE THIS INTO 1 SINGLE STAGE IF WE REALLY WANT
  // TO: by setting the address in a table and action parameter for the simple
  // set base adress 
  apply(out_port_to_offsets);

  // Always read or try to update
  apply(read_update_zooming_stage); // we need the logic to add one to this at the very end
  apply(read_update_max_0);
  apply(read_update_max_1);

  /* For the experiment we will need to update this when 
     we see STOPS or at the end counter compute exchanges */
  apply(read_out_state);
  
  // If 
  if (valid(fancy) and fancy.action_value == MULTIPLE_COUNTERS)
  {   
      // (valid(fancy_pre) and fancy_pre.pre_type >= UPDATE_MAX_0)
      // this means that there is no counters
      if (valid(fancy_pre) and ((fancy_pre.pre_type & 0x20) != 0))
      {
        apply(drop_egress);
      }

      else if (valid(fancy_counters_length))
      {
        // Read and reset local counter -> can be reset since the packet 
        // was received, and we can use this for the next round.
        apply(table_read_reset_counter);

        // subtracts local and remote counter to see packet difference
        apply(subtract_counters);

        // Last layer drops
        if (egr_meta.zooming_stage == MAX_ZOOM and egr_meta.local_counter_and_diff != 0)
        {
          apply(build_egr_hash_path);
        }

        // substract with saturation if 
        apply(subtract_differences); 

        // update max values from the packet header fancy_pre
        if (egr_meta.counter_diff_excess == 0) 
        {
            apply(update_max_values);
        }        
        
        // sets packet to update zooming, max, etc
        apply(set_fancy_pre_type_to_update);
      }
  }

  else if (valid(ipv4) and egr_meta.state == SENDER_COUNTING)
  {    
    // add dpdf header 
    if (not valid(fancy))
    {
        apply(add_fancy_counting_header);
    }

    if (egr_meta.zooming_stage == 0)
    {
        apply(set_zoom_address_0);
    } 
    else if (egr_meta.zooming_stage == 1 and egr_meta.max_0 == br_meta.hash_0)
    {
        apply(set_zoom_address_1);
    }
    #ifdef SDE8
    else if (egr_meta.zooming_stage == 2 and egr_meta.max_0 == br_meta.hash_0)
    {
        if (egr_meta.max_1 == br_meta.hash_1)
        {
            apply(set_zoom_address_2);
        }
    }
    #endif
    #ifdef SDE9
    else if (egr_meta.zooming_stage == 2 and egr_meta.max_0 == br_meta.hash_0 and egr_meta.max_1 == br_meta.hash_1)
    {
        apply(set_zoom_address_2); 
    }
    #endif

    // counting
    if (egr_meta.count_packet_flag == 1)
    { 
        apply(add_to_array);
    }
    else 
    {
        // remove header that we added automatically
        apply(remove_fancy_header);
    }
  }
  /* TEMPORAL */
  else if (valid(fancy) and valid(ipv4) and egr_meta.state == 0)
  {
    apply(remove_fancy_header2);
  }

}   