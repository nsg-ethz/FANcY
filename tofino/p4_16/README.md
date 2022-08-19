# FANcY's Tofino P4-16 implementation

In this page, you will find all the necessary code and documentation to run
`FANcY's` hardware implementation in `p4_16`. That includes the P4 code itself,
controllers, utility scripts and an orchestrator to automate different runs.

* The `eval` folder contains `tofino-16-test.py` which is a script that is able to
  run all the different evaluation experiments. For that the script uses TCP
  `sockets` to send commands to different components involved in the eval such
  as the receiver server and the Tofino switches.

* The `scripts` folder contains a set of utilities used by all the other scripts.

* The `p4src` folder contains the code of `fancy` and also some special switch
  code called `middle_switch.p4`, which we use as a middle switch between
  fancy's upstream and downstream state machines. This switch is in charge of
  adding some packet drops when instructed. For `fancy`, you will find
  `fancy.p4` and multiple include files which contain the ingress and egress of
  the different components. Everything has been tested with both `SDE 9.7.3` and
  `SDE 9.9.0`.
  
* We provide the control plane for both programs. You can find them at the
  `control_plane` folder or in the middle switch folder. Both control planes are
implemented using the `bfrt` API. In order to make the controller code a bit
simpler, we include the `bfrt_helper` folder with some API wrappers.  Both
controllers run a command server that we use to remotely orchestrate the
experiments. We also add some simple `run_pd_rpc.py` scripts that used the fixed
API to set the ports and traffic generator in the hardware switch.


## Setup requirements

To run our case study, you will need to have a setup with the following:

* Two Intel Tofino Switches. We used the Wedge 100BF-32X. 
    * Both `FANcY` and `middle_switch` can run with SDE version 9.7.0-9.9.0. 
    * As opposed to our P4_14 version, all scripts have been ported to
      `python3`. They should, however still work for `python2`.
    * If any of your switches is running on an old SDE (9.5 or less), make sure you set it up
    accordingly, as shown below:
      ```
      sudo ln -sf $(which python2) /usr/bin/python
      ```
    * You need to make sure your `run_pd_rpc.py` runs with `python2`, and thus
      its code starts with `#!/usr/bin/python2`
    * You need to install scapy for `python2`: `pip2 install scapy==2.4.3`.
      Usually it gets installed with the SDE, so probaly you won't have to do
      anything.


* You need two servers. One sender and one receiver.
    * Each server should have at least one 100Gbe NIC. We used Mellanox ConnectX-5
      100Gbps NIC.
    * You need to install `iperf-2.1.0`. We use a flag (`--sum-only`), that is
      not available on the `iperf` version you get from `apt-get`. To install it
      you can simply do the following:
        ```
        Install iperf version
        wget https://sourceforge.net/projects/iperf2/files/iperf-2.1.0-rc.tar.gz
        tar -xvf iperf-2.1.0-rc.tar.gz
        cd iperf-2.1.0-rc/
        ./configure; make; sudo make install
        # make sure it has updated
        ```
    * You need internet connectivity from the sender to the receiver and the
      Tofino switches. The orchestrator needs that to send commands. Thus, make
      sure that there is connectivty, and the ports you use are open.

## Topology and setup

In order to successfully run the evaluation you will need to setup your testbed
as depicted in the figure below:

![Hardware Setup](../fancy-setup.png)

In the figure, you can see that we are using two servers, one sender and one
receiver. Each is connected two the first switch, `tofino1` (name in our
setup), which is running one of the `FANcY` programs.  Note, that we connect them
to port 7 (176) and 8 (184) respectively. Then, `tofino1` is connected to `tofino4` using
3x100G cables:
 * Main link: this is the link `fancy` uses to send traffic to `dst` through `tofino4`. And used by `tofino4` to send traffic to `src` when it comes form `dst`.
 * Return link:  the same but for traffic from and to `dst`.
 * Backup path: this is the link `fancy` uses to send traffic from `src` to `dst` when a failure is detected.

The second switch, `tofino4` is running the program `middle_switch.p4`. That is a special program that simply forwards
packets as described above, and as you can see in the figure. Furthermore, it can be configured to drop some `%` of
packets. This configuration can be done at `Runtime` through the controller.

:warning: **Important**: 

Apart from the physical and internal port numbers, you can see that each port also has a port
name of the form `PORTX_S`. Those port names are important and are hardcoded in the [`fancy/includes/constants.p4`
file](./fancy/includes/constants.p4#L65). In case you want to use different tofino ports, you must also update the
mappings there and recompile the program. Control plane code also depends on those constant `#defines`.

## How to run and reproduce paper results

:hourglass_flowing_sand: Once you have all installed, running the experiments is relatively easy. The expected time to
run the following experiments is 20 minutes. :hourglass_flowing_sand:

### Preliminary steps

1. Copy the tofino folder in the servers and tofino switches. Alternatively pull the entire repository. In the following example we have copied the content of the tofino folder to `~/fancy/`. 
2. Make sure the right `iperf` is installed in both servers. If not read the requirements section and install `iperf`. 
    ```
    $ iperf -v
    iperf version 2.1.0-rc (5 Jan 2021) pthreads
    ```
3. Make sure `scapy` is installed in the switches for `python3`.
    ```
    $ pip list | grep scapy
    scapy  2.4.3
    ```
4. Configure sender and receiver `IPs` and `ARP` table (just in case ARP messages are not being flooded). For that you
   can use [`../scripts/server_setup.sh`](../scripts/server_setup.sh) utility. Do the same for both sender and receiver, but
   swap the ips and use the mac address of the other side. For example:
    ```
    cd ~/fancy/scripts/
    ../server_setup.sh <intf> <src ip> <dst ip> <dst mac>
    ```
5. Make sure you have the `env variables` pointing to `SDE 9.9.0` in both tofino switches.
    ```
    $ echo $SDE
    /data/bf-sde-9.9.0
    ```

6. Compile `fancy.p4` at the first switch (`tofino1`).
    ```
    # first program
    ~/tools/p4_build.sh -D HARDWARE -D REROUTE --with-tofino --no-graphs fancy.p4


    Note that our `p4_build` script is called `p4_build.sh`. And we are using several preprocessor (`-D`) parameters.
    Also, we assume the code is placed at `~/fancy/`.

7. Compile `middle_switch.p4` at the second switch (`tofino4`)
    ```
    ~/tools/p4_build.sh --with-tofino --no-graphs middle_switch.p4
    ```

Now, we are almost all set to start the experiments! :rocket:

### Running the experiments

Now we will run the experiments needed to get the case study `figure 8` from the paper. To make the experiments simple we will use [`eval/tofino-16-test.py`](../eval/tofino-16-test.py) which is an orchestrator that will make our life very easy.

In order for the orchestrator to know how to send commands to the other server and tofino switches, you will need to  modify the contents of `eval/server_mappings.py` with the IP (public or private) of your two servers and switches. You will find some default ports, but feel free to change them if needed. 

```
remote_mappings = {
    "tofino1": ("<tofino ip>", 5000),
    "tofino4": ("<tofino ip>", 5001),
    "sender": ("<sender server ip>", 31500),
    "receiver": ("<receiver server ip>", 31500)
}
```

Everything is ready to start the experiments.

#### Running the experiments

1. Start the command server at the receiver server. 
    ```
    cd ~/fancy/eval
    python3 command_server.py --port 31500
    ```

2. Start the `middle_switch` at `tofino4`. 
    ```
    $SDE/run_switchd.sh -p middle_switch
    ```

3. Start control plane for the `middel_switch` at `tofino4`.
    ```
    cd ~/fancy/p4_16/fancy/middle_switch/ 
    python3 -i control_plane.py
    ```

4. Start `fancy` at `tofino1`. 
    ```
    $SDE/run_switchd.sh -p fancy
    ```

5. Start control plane for `fancy` at `tofino1`.
    ```
    cd ~/fancy/p4_16/fancy/control_plane/
    ipython3 -i control_plane.py -- --server --server_port 5000
    ```

6. Start the orchestrator at the sender server and run dedicated entries tests
    ```
    cd ~/tofino-fancy/eval
    sudo python3 tofino-16-test.py --test_type dedicated --output_dir ~/dedicated_outputs/ --remote_server receiver
    ```

7. Wait 3 minutes, all the results will be stored at `~/dedicated_outputs/`


8. Start the orchestrator at the sender server and run zooming entries tests
    ```
    cd ~/tofino-fancy/eval
    ssudo python3 tofino-16-test.py --test_type zooming --output_dir ~/zooming_outputs2/ --remote_server receiver
    ```

9. Wait 3 minutes, all the results will be stored at `~/zooming_outputs2/`

#### Plotting

In order to get the plot out, you can move to the [sigcomm evaluation
page](../../eval_sigcomm2022/README.md#running-tofino-case-study/). 
