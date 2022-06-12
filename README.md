# FANcY: FAst In-Network GraY Failure Detection for ISPs

This repo contains the implementation of the paper [FANcY: FAst In-Network GraY
Failure Detection for ISPs](.) by Edgar Costa Molero, Stefano Visicchio and
Laurent Vanbever. This work will be presented at [SIGCOMM
'22](https://conferences.sigcomm.org/sigcomm/2022/cfp.html)

## Abstract
Avoiding packet loss is crucial for ISPs. Unfortunately, gray failures at ISP
switches cause long-lasting packet drops which are undetectable by existing
monitoring tools. In this paper, we describe the design and implementation of
FANcY, an ISP-targeted system that detects and localize gray failures quickly
and accurately. FANcY complements previous monitoring approaches, which do not
work at the ISP scale. We experimentally confirm FANcY’s capability of
accurately detecting gray failures in seconds, unless only tiny fractions of
traffic experience losses. We also implement FANcY in an Intel Tofino switch,
and demonstrate how it enables fine-grained fast rerouting.

## What can you find in this repository 

* **SIGCOMM 2022 eval:** contains a step-by-step guide to reproduce the results
  from the SIGCOMM 2022 paper. You can also find a set of scripts to easily run
  all the simulation-based evaluations, pre-compute outputs and generate the
  paper plots. 

* **Installation:** few scripts that are used to install all the required
  dependencies for the `ns3` simulator.

* **Simulation:** git submodule to our modified `ns3` simulator. Among others,
  it includes all the scripts for the simulation-based evaluation. An
  implementation of `FANcY`,
  [NetSeer](https://dl.acm.org/doi/abs/10.1145/3387514.3406214) and
  [LossRadar](https://dl.acm.org/doi/10.1145/2999572.2999609) in `ns3`.

* **Experiments:** python `fancy` package used to parse, orchestrate, and plot
  the simulation-based experiments.

* **Tofino:** contains the hardware-based implementation of `FANcY`, its
  controller and some helper scripts. Furthermore, it contains a guide to
  reproducing the `case study` and `figure 8` from the paper.

## Quick Install

In order to run the simulations, you have to install our `fancy` python package
and the `ns3` simulator with our custom code. 

1. Create a folder called `fancy` at your `HOME`.
```
mkdir ~/fancy/
```

2. Clone this repository there. 
```
cd ~/fancy/
# get main repo
git clone git@gitlab.ethz.ch:nsg/employees/cedgar/projects/fancy/sigcomm-2022-fancy-code.git fancy-code
# get submodules (simulator)
cd fancy-code
git submodule update --init
```

3. Install our custom `ns3`. Select `Y` when prompted. 
```
cd ~/fancy/fancy-code/installation
./install-ns3.sh
```

3. Install the `fancy` python package and python dependencies. 
```
cd ~/fancy/fancy-code/experiments/
pip3 install -e .
```

Alternatively, you can download the provided VM with the software installed and
input files downloaded.

## Contact

Feel free to drop us an email at `cedgar at ethz dot ch` if you have any questions.