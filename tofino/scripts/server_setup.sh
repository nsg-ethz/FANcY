#!/bin/bash

# Simple command line parameters 
intf=$1
src_ip=$2
dst_ip=$3
dst_mac=$4

# bring interface down
sudo ifconfig ${intf} down

# delete address if existed?
sudo ip address del ${src_ip}/24 dev ${intf}

# bring interface up
sudo ifconfig ${intf} up

# set ip address
sudo ip address add ${src_ip}/24 dev ${intf}

# set arp table just in case arp forwarding does not work
sudo arp -i ${intf} -s ${dst_ip} ${dst_mac}

# disable ipv6
sudo sysctl net.ipv6.conf.${intf}.disable_ipv6=1
