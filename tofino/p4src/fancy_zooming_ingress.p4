header_type ingress_meta_t {
    fields {
        state: 8;
        simple_address: 8;
        counter_address: 16;
        bf_1: 1;
        bf_2: 1;
    }
}

// Hash stufff

field_list egr_hash_path_list {
  fancy_pre.hash_0;
  fancy_pre.hash_1;
  fancy_pre.hash_2;
}

field_list ing_hash_path_list {
  br_meta.hash_0;
  br_meta.hash_1;
  br_meta.hash_2;
}

field_list_calculation ing_hash_1 {
    input {ing_hash_path_list;}
    algorithm: crc32;
    output_width: 16;
}

field_list_calculation ing_hash_2 {
    input {ing_hash_path_list;}
    algorithm: crc_32c;
    output_width: 16;
}

field_list_calculation egr_hash_1 {
    input {egr_hash_path_list;}
    algorithm: crc32;
    output_width: 16;
}

field_list_calculation egr_hash_2 {
    input {egr_hash_path_list;}
    algorithm: crc_32c;
    output_width: 16;
}

register bloom_filter_1 {
    width: 1;
    instance_count: 65536;
}

register bloom_filter_2 {
    width: 1;
    instance_count: 65536;
}

blackbox stateful_alu alu_bloom_filter_1_set {
    reg: bloom_filter_1;

    update_lo_1_value: set_bit;
    output_value: alu_lo;
    output_dst: ing_meta.bf_1;
}

blackbox stateful_alu alu_bloom_filter_1_read {
    reg: bloom_filter_1;

    update_lo_1_value: read_bit;
    output_value: alu_lo;
    output_dst: ing_meta.bf_1;
}

blackbox stateful_alu alu_bloom_filter_2_set {
    reg: bloom_filter_2;

    update_lo_1_value: set_bit;
    output_value: alu_lo;
    output_dst: ing_meta.bf_2;
}

blackbox stateful_alu alu_bloom_filter_2_read {
    reg: bloom_filter_2;

    update_lo_1_value: read_bit;
    output_value: alu_lo;
    output_dst: ing_meta.bf_2;
}

action _bloom_filter_1_set () {
    // clear
    modify_field(fancy_pre.set_bloom, 0);
    alu_bloom_filter_1_set.execute_stateful_alu_from_hash(egr_hash_1);
}

action _bloom_filter_2_set () {
    // clear
    //modify_field(fancy_pre.set_bloom, 0);
    alu_bloom_filter_2_set.execute_stateful_alu_from_hash(egr_hash_2);
}

#ifdef SDE8
@pragma stage 4
#endif
table bloom_filter_1_set {
    actions {
        _bloom_filter_1_set;
    }
    default_action: _bloom_filter_1_set ();
    size: 1;
}

#ifdef SDE8
@pragma stage 5
#endif
table bloom_filter_2_set {
    actions {
        _bloom_filter_2_set;
    }
    default_action: _bloom_filter_2_set ();
    size: 1;
}

action _bloom_filter_1_read () {
    alu_bloom_filter_1_read.execute_stateful_alu_from_hash(ing_hash_1);
}

action _bloom_filter_2_read () {
    alu_bloom_filter_2_read.execute_stateful_alu_from_hash(ing_hash_2);
}

#ifdef SDE8
@pragma stage 4
#endif
table bloom_filter_1_read {
    actions {
        _bloom_filter_1_read;
    }
    default_action: _bloom_filter_1_read ();
    size: 1;
}

#ifdef SDE8
@pragma stage 5
#endif
table bloom_filter_2_read {
    actions {
        _bloom_filter_2_read;
    }
    default_action: _bloom_filter_2_read ();
    size: 1;
}


// End of hash stuff

register in_counters {
    width : 32;
    instance_count : 1024;
    attributes : saturating;
}

register in_state {
    width : 8;
    instance_count : 32;
}

action drop_exit_ingress() {
  modify_field(ig_intr_md_for_tm.drop_ctl, 1);
  exit();
}

/* Field list definitions */    
field_list hash_fields {
  ipv4.dstAddr;
}

field_list_calculation hash0 {
    input {hash_fields;}
    algorithm: poly_0x11021_not_rev_init_0xffff;
    output_width: 16;
}

field_list_calculation hash1 {
    input {hash_fields;}
    algorithm: crc_16_dect;
    output_width: 16;
}

field_list_calculation hash2 {
    input {hash_fields;}
    algorithm: crc_16_dnp;
    output_width: 16;
}

action do_compute_hashes()
{
    modify_field_with_hash_based_offset(br_meta.hash_0, 0, hash0, COUNTER_NODE_WIDTH);
    modify_field_with_hash_based_offset(br_meta.hash_1, 0, hash1, COUNTER_NODE_WIDTH);
    
    #ifdef SDE9
    modify_field_with_hash_based_offset(br_meta.hash_2, 0, hash2, COUNTER_NODE_WIDTH);
    #endif
}

table compute_hashes {
  actions {
    do_compute_hashes;
  }
  default_action: do_compute_hashes();
  size: 1;
}

action do_compute_hashes1()
{
    modify_field_with_hash_based_offset(br_meta.hash_2, 0, hash2, COUNTER_NODE_WIDTH);
}

table compute_hashes1 {
  actions {
    do_compute_hashes1;
  }
  default_action: do_compute_hashes1();
  size: 1;
}

action set_ingress_address_offsets_normal(counter_offset, simple_offset) {
    // CAREFUL THIS SUM MIGHT BE A PROBLEM IN SOME SCENARIOS
    add(ing_meta.counter_address, counter_offset, fancy.seq); // counter value carries the hash (bucket) offset 
    modify_field(ing_meta.simple_address, simple_offset);
}

action set_ingress_address_offsets_recirc(counter_offset, simple_offset) {
    // CAREFUL THIS SUM MIGHT BE A PROBLEM IN SOME SCENARIOS
    add(ing_meta.counter_address, counter_offset, fancy_counters_length._length); // counter value carries the hash (bucket) offset 
    modify_field(ing_meta.simple_address, simple_offset);
}

table in_port_to_offsets {
    reads {
        fancy_pre.valid: exact;
        ig_intr_md.ingress_port: ternary;
        fancy_pre.port: ternary;
    }
    actions {
        set_ingress_address_offsets_normal;
        set_ingress_address_offsets_recirc;
        _NoAction;
    }
    default_action: _NoAction ();
    size: 32;
}

blackbox stateful_alu read_in_state {
    reg     : in_state;

    output_value    :   register_lo;
    output_dst      :   ing_meta.state;
}

action _read_in_state()
{
    read_in_state.execute_stateful_alu(ing_meta.simple_address);
}

table read_in_state {
    actions {
        _read_in_state;
    }
    default_action: _read_in_state ();
    size: 1;
}

action _set_generating_multiple_counters()
{
  // pre header
  add_header(fancy_pre);
  modify_field(fancy_pre.pre_type, 0);
  modify_field(fancy_pre.port, ig_intr_md.ingress_port);
  modify_field(ethernet.etherType, FANCY_PRE);

  // Add fancy counters header 
  add_header(fancy_counters_length);
  modify_field(fancy.action_value, GENERATING_MULTIPLE_COUNTERS);
  modify_field(fancy_counters_length._length, 0);
}

table set_generating_multiple_counters {
  actions {
    _set_generating_multiple_counters;
  }
  default_action: _set_generating_multiple_counters();
  size: 1;
}



blackbox stateful_alu read_counter {
    reg     : in_counters;

    update_lo_1_value: 0; //register_lo; to reset

    output_value    :   register_lo;
    output_dst      :   fancy_counter.counter_value;
}

blackbox stateful_alu add_to_counter {
    reg     : in_counters;

    update_lo_1_value: register_lo + 1;

    output_value    :   alu_lo;
    output_dst      :   fancy_counter.counter_value;
}

action _add_to_counter(){
   add_to_counter.execute_stateful_alu(ing_meta.counter_address);
}

table table_add_to_counter {
  actions {
    _add_to_counter;
  }
  default_action: _add_to_counter();
  size: 1;
}

action _read_counter(){
   read_counter.execute_stateful_alu(ing_meta.counter_address);
}

table table_read_counter {
  actions {
    _read_counter;
  }
  default_action: _read_counter();
  size: 1;
}

action _add_fancy_counter(){
    add_header(fancy_counter);
    add_to_field(fancy_counters_length._length, 1);
    //modify_field(fancy_counter.counter_value, ing_meta.counter_value);
}

table add_fancy_counter {
    actions {
        _add_fancy_counter;
    }
    default_action: _add_fancy_counter();
    size: 1;
}

action _recirculate_counter_read(){
    recirculate(68);
    exit();
}

table recirculate_counter_read {
    actions {
        _recirculate_counter_read;
    }
    default_action: _recirculate_counter_read();
    size: 1;    
}

action _return_counter()
{
  // sets initial port
  modify_field(ig_intr_md_for_tm.ucast_egress_port, fancy_pre.port);
  modify_field(ethernet.etherType, FANCY);
  modify_field(fancy.action_value, MULTIPLE_COUNTERS);

  // remove pre header since its internally used for recirculation
  remove_header(fancy_pre);

  //bypass egress
  bypass_egress();
}

table return_counter{
  actions {
    _return_counter;
  }
  default_action: _return_counter();
  size: 1;
}

action _set_computing_multiple_counters()
{
  // pre header
  add_header(fancy_pre);
  modify_field(fancy_pre.set_bloom, 0);
  modify_field(fancy_pre.pre_type, 0);
  modify_field(fancy_pre.port, ig_intr_md.ingress_port);
  modify_field(ethernet.etherType, FANCY_PRE);
  modify_field(fancy_pre.max_index, 0);
  modify_field(fancy_pre.max_counter_diff, 0);

  // Add fancy counters header 
  //add_header(fancy_counters_length);
  //modify_field(fancy.action_value, GENERATING_MULTIPLE_COUNTERS);
  //modify_field(fancy_counters_length._length, 0);
}

table set_computing_multiple_counters {
  actions {
    _set_computing_multiple_counters;
  }
  default_action: _set_computing_multiple_counters();
  size: 1;
}

action _sub_fancy_counter(){
    add_to_field(fancy_counters_length._length, -1);
}

table sub_fancy_counter {
    actions {
        _sub_fancy_counter;
    }
    default_action: _sub_fancy_counter();
    size: 1;
}

action _recirculate_counter_compute(){
    recirculate(68);
}

table recirculate_egress {
    actions {
        _recirculate_counter_compute;
    }
    default_action: _recirculate_counter_compute();
    size: 1;
}

action set_port(outport)
{ 
    // Why was this needed?
    //modify_field(fancy.action_value, MULTIPLE_COUNTERS);
    modify_field(ig_intr_md_for_tm.ucast_egress_port, outport);
    modify_field(ethernet.srcAddr, 1);
}

table forward {
  reads{
    ig_intr_md.ingress_port: exact;
  }
  actions {
    set_port;
    _NoAction;
  }
  default_action: _NoAction();
  size: 32;
}

/* Simple rerouting action that just sets the port to the backup */
table reroute {
  actions {
    set_port;
  }
  #ifdef HARDWARE
  default_action: set_port(PORT6_S);
  #else
  default_action: set_port(PORT6_M);
  #endif 
  size: 1;
}

#ifdef HARDWARE
action _exit(){
    exit();
}

table exit_ingress{
    actions{
        _exit;
    }
    default_action: _exit ();
    size: 1;
}
#endif

/*INGRESS PIPE*/
control ingress_ctrl {

  // Compute packet hashes
  apply(compute_hashes);
  // needed to split it for some reason
  #ifdef SDE8
  apply(compute_hashes1);
  #endif

  // Forward the packet
  apply(forward); 

  apply(in_port_to_offsets);
  apply(read_in_state);

  /* This can be done with the internal traffic generator*/
  /* Forwards a STOP message  to the egress machine */
  #ifdef HARDWARE
  if ((ig_intr_md.ingress_port == PORT4_S) and valid(fancy) and fancy.action_value == STOP)
  {
      apply(exit_ingress);
  }
  #endif
   
   // Send counters back
   // Only do if in counting state and receive a STOP, but we will need a SUBCOUNTING STATE
  if (valid(fancy) and (fancy.action_value == GENERATING_MULTIPLE_COUNTERS or fancy.action_value == STOP))
  {   
      if (not valid(fancy_counters_length))
      {
        apply(set_generating_multiple_counters);
      }

      //  build counter packet 
      if (fancy_counters_length._length != COUNTER_NODE_WIDTH) // this should be > but... this is an ungly workaround
      {
          // Increase fancy_counters_length and append one counter
          apply(add_fancy_counter);

          // reads and resets the counter // THIS NEEDS TO BE DIFFERENT WHEN ACKNOWLEDGES
          apply(table_read_counter);

          // recirculate
          apply(recirculate_counter_read);
      }

      else //(fancy_counters_length._length == COUNTER_NODE_WIDTH) 
      {
          // Send it back to the original port it came in
          apply(return_counter);
      }
  }

  // This sends always the packet to the egress, and shpuld not use it to count anything
  else if (valid(fancy) and fancy.action_value == MULTIPLE_COUNTERS and fancy.fsm == 1)
  {   
      // if first recirculation we add the fancy_pre header, and store port
      if (not valid(fancy_pre))
      {
        apply(set_computing_multiple_counters);
      }
      // subtract 1 to length and remove header already (if we dont have stage move this down)
      // do not substract if its < 0, a saturating field did not work..
      if (fancy_counters_length._length != 0)
      {     
          apply(sub_fancy_counter);
      }
      apply(recirculate_egress);
  }

  // This is our main counting part, this can only be done if at counting and count flag is set.
  else if (valid(ipv4) and ing_meta.state == RECEIVER_COUNTING and valid(fancy) and fancy.count_flag == 1)
  {
      // count ingress side packets
      // the register offet is stored in the counter
      apply(table_add_to_counter);
  }

  // REROUTING LOGIC, not sure it should be tight to any state probably not.
  if (valid(fancy_pre) and fancy_pre.set_bloom == 1) // this comes from egress when recirculating
  {
      apply(bloom_filter_1_set); 
      apply(bloom_filter_2_set);
  }

  /* WARNING: For simplicity we only reroute ports coming from PORT X. To generalize we would have to do some small modifications */
  #ifdef HARDWARE
  else if (valid(ipv4) and (ig_intr_md.ingress_port == PORT4_S)) 
  #else
  else if (valid(ipv4) and (ig_intr_md.ingress_port == PORT4_M)) 
  #endif
  {
      apply(bloom_filter_1_read);
      apply(bloom_filter_2_read);

      /* if the bloom filter is set we reroute */
      if ((ing_meta.bf_1 == 1) and (ing_meta.bf_2 == 1))
      {
        apply(reroute);
      }
  }
}
