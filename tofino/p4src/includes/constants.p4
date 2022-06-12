/* CONSTANTS */

#define MAX32 2147483647 // max positive number..
#define MAX_ZOOM 2 // 3 zooms
#define COUNTER_NODE_WIDTH 32

/* Globals */
#define NB_REGISTER_SIZE 4096
 // they should not happen
#define RETRANSMIT_AFTER 100
// Number of packets to count before 
// Dedicated counter exchange. 
// With the internatl traffic generator
// this can be changed to time
#define PACKET_COUNT 100000

/* Protocols */
#define IPV4 0x0800
#define ARP  0x0806
#define IPV6 0x86DD
#define FANCY 0x0801
// Fancy pre header
#define FANCY_PRE 0x0802
#define LLDP 0x88cc
#define TCP  6
#define UDP  17

/* MODEL PORT NUMBERING */
#define PORT0_M 0 
#define PORT1_M 1
#define PORT2_M 2
#define PORT3_M 3
#define PORT4_M 4   
#define PORT5_M 5
#define PORT6_M 6

/* Tofino */
// Debugging port. Used to clone packets for some important events.
#define PORT0_S 128 /* server 1/2 - 10g interface. tofino port 1 */ 

/* ATENTION:
    Port naming is very important and for simplicity it has been hardcoded into 
    some places. You must connect your cables in the following way for the experiments
    to work.

    PORT1_S: Is the port between the main switch and the switch that add failures.
    PORT2_S: Is the return path for packets that come from the receiver 
             back to the sender through the intermediate switch.
    PORT3_S: Not used.
    PORT4_S: Sender port. This is a 100G port attached to the sending server.
    PORT5_S: Receiver port. This is a 100G port attached to the receiving server.
    PORT6_S: Backup port. This port connects the main switch with the intermediate 
             switch and it used to reroute traffic being affected by the failure.
*/

// SENDER PORT
#define PORT4_S 176  /* Server 1 PHY PORT 7 */
// Receiver Port
#define PORT5_S 184  /* pisco 100g interface tofino port 8*/

// Main input port.
#define PORT1_S 152 //152 /* tofino port 4*/
// Return path
#define PORT2_S 168 //168 /* tofino port 6*/
// Backup port
#define PORT6_S 144 /* tofino port 3 -> reroute port */
// Not used for the eval
#define PORT3_S 52 /* Server 1 second port, PHY 10 */

#define NUM_DEDICATED_ENTRIES 512
#define ENTRY_ZOOM_ID 511

/* PORTS ID MAPPINGS */
/* Mappings for dedicated counter entries register cell*/
#define PORT0_ID 0
#define PORT1_ID 512
#define PORT2_ID 1024
#define PORT3_ID 1532
#define PORT4_ID 2048
#define PORT5_ID 2560
#define PORT6_ID 3072

/* FANCY ACTIONS */
#define KEEP_ALIVE 0
#define START     1
#define STOP      2
#define COUNTER   4  //Packet contains a single counter

/* ADVANCED IMPL*/
#define MULTIPLE_COUNTERS 16
#define GENERATING_MULTIPLE_COUNTERS 8 //for debugging

/* State Machine State Sender*/

/* STATES */
#define SENDER_IDLE 0
#define SENDER_START_ACK 1
#define SENDER_COUNTING 2
#define SENDER_WAIT_COUNTER_RECEIVE 3

/* COUNTER CONSTANTS */
#define SENDER_IDLE_COUNT 1
// COUNTER STOP TRIGGER
#define SENDER_COUNTING_COUNT PACKET_COUNT
// RETRANSMITS
#define SENDER_WAIT_COUNTER_RECEIVE_COUNT RETRANSMIT_AFTER
#define SENDER_START_ACK_COUNT RETRANSMIT_AFTER

/* State Machine State Reciver*/

/* STATES */
#define RECEIVER_IDLE 0
#define RECEIVER_COUNTING 1
#define RECEIVER_WAIT_COUNTER_SEND 2
#define RECEIVER_COUNTER_ACK 3

/* COUNTER CONSTANTS */
#define RECEIVER_WAIT_COUNTER_SEND_COUNT 1
// RETRANSMITS
#define RECEIVER_COUNTER_ACK_COUNT RETRANSMIT_AFTER

/* Control types*/
#define STATE_UPDATE_INGRESS 1
#define STATE_UPDATE_EGRESS 2
#define INGRESS_SEND_COUNTER 3
#define REROUTE_RECIRCULATE 4

#define UPDATE_OFFSET 32
#define UPDATE_MAX_0 36 // 32 + 4
#define UPDATE_MAX_1 37 // 32 + 5


/* Counter Modification Types */
#define COUNTER_UNTOUCHED 0
#define COUNTER_INCREASE 1
#define COUNTER_RESET 2

/* LOCK RETURNS*/
#define LOCK_VALUE 10

/* Stage 2 state change*/
/* h l
/* 0 0 -> 1 LOCK_NONE
/* 0 1 -> 2 LOCK_RELEASED
/* 1 0 -> 4 LOCK_OBTAINED
/* 1 1 -> 8 LOCK_ERROR
*/
#define LOCK_NONE 1  
#define LOCK_RELEASED 2
#define LOCK_OBTAINED 4
#define LOCK_ERROR 8

/* EGRESS AND INGRESS TYPES */
#define SWITCH 2
#define HOST 1