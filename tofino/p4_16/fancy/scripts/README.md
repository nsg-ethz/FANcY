# build
~/tools/p4_build.sh --with-tofino --no-graphs fancy_dedicated.p4

# run
$SDE/run_switchd.sh -p fancy_dedicated
$SDE/run_tofino_model.sh -p fancy_dedicated

# control plane
ipython3 -i control_plane.py

# set link
# parser.add_argument('--intf1', type=str, required=False, default="veth2")
# parser.add_argument('--intf2', type=str, required=False, default="veth4")
# parser.add_argument('--connected', type=bool,
#                     required=False, default=False)
# parser.add_argument('--mindelay', type=float, required=False, default=0)
# parser.add_argument('--maxdelay', type=float, required=False, default=0)
# parser.add_argument('--loss1', type=float, required=False, default=0)
# parser.add_argument('--loss2', type=float, required=False, default=0)
# parser.add_argument('--fail_ips', type=str, required=False, default='')

sudo python link.py  --mindelay 0.01 --maxdelay 0.01 --connected True --intf1 veth2 --intf2 veth4 --fail_ips "11.0.2.2"
# to listen to rerouted packets!
sudo python link.py --intf1 veth12 --intf2 ""

# send packets
# def send_fancy_packet(
#        iface, action, count, ack, fsm, counter_value=0, number=1, delay=0,
#        multiple_counters=None, mlength=32):

# regular packet
send_packet("veth8", addr="11.0.2.2", count=1, delay=0.3)

# fancy packet

send_fancy_packet("veth2", actions["MULTIPLE_COUNTERS"], 0, 0, 1, 0, 1, 0, [65, 64], 2)

send_fancy_packet("veth2", actions['COUNTER'], 0, 0, 1,id=1)
send_fancy_packet("veth8", actions['STOP'], 0, 0, 1, id=1)