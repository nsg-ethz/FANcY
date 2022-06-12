# SIGCOMM 2022 Evaluation 

This folder contains all the necessary materials to reproduce the results of
FANcY's SIGCOMM 2022 paper. 

You can either install all the dependencies and build the `ns3` simulator in
your Ubuntu machine (preferably Ubuntu 18.04) or you can directly use the
virtual machine we provide
([VM](https://polybox.ethz.ch/index.php/s/CzZRqYXe6EUGr0L/download)). The
virtual machine has all the dependencies installed with all the required
datasets as well as a clone of this repository at `~/fancy`. 

## Installation 

You can install all the required software to run most of the evaluation directly
on your server (we provide install scripts for Ubuntu 18.04 LTS) or you can use
the provided VM ([see next section](#downloading-and-adding-virtual-machine)). 

If you decide to run in a bare metal server, follow the [quick install
guide](../README.md#quick-install). Otherwise follow the steps below.
## Downloading and Adding Virtual Machine

To install our VM, you will need to have `kvm`, `qemu` and `virt-manager`
installed on your machine. You can find a guide for a Ubuntu system on
the following [page](https://phoenixnap.com/kb/ubuntu-install-kvm).

The next step is to set up the actual virtual machine. For that
[download](https://polybox.ethz.ch/index.php/s/CzZRqYXe6EUGr0L/download) it, and
extract it on your machine: `tar -xvf fancy-vm.tar.gz`. Next, start up the
`virt-manager`. Create a new virtual machine, and choose `Import existing disk
image and provide the extracted image (by clicking Browse, followed by Browse
Locally`. As the operating system, choose Ubuntu 18.04 LTS. Give the VM as many
CPUs as possible and at least 64GB of RAM (more if possible). We later provide
expected run times for a machine with 64 cores and 256GB of RAM.

:bulb: **VM credentials:**
Username: `fancy`
Password: `fancy2pass`

## Running the experiments

In this section, we will run all the experiments and simulations to reproduce
the results from the paper one by one. To make it easier, we provide some
scripts that will automate the process. First, we generate all the required
`ns3` simulation commands (in a text file) and run them. After, we process the
outputs and generate `precomputed` results. Finally, we generate all the plots.
We generate the following plots and tables:

1. **Figure 2:** Analytical study of total memory needed by `NetSeer` as the
   inter-switch link latency increases. 
2. **Figure 5:** Accuracy and detection speed of dedicated counter for different
   gray failures and traffic volumes.
3. **Figure 6:** Evaluation showing the minimum entry/prefix size to achieve 95%
   detection rate for different zooming speeds. 
4. **Figure 7a:** Accuracy and detection speed of FANcY's hash-based tree for
   different loss rates, prefix sizes and single-entry failures.
5. **Figure 7b:** Accuracy and detection speed of FANcY's hash-based tree for
   different loss rates, prefix sizes and 100-entry failures.
6. **Section 5.1.3:** We evaluate the accuracy and detection speed of FANcY for
   uniform random drops. Results are displayed in the form of a table named
   `uniform_random_drops.txt`
7. **Table 3:** Evaluation showing the average accuracy and detection speed of
   FANcY over some CAIDA traces. In this experiment, we fail the top 10k
   prefixes one by one, for different loss rates. Results are shown in the form
   of a text table (`table3_reduced.txt`).
8. **Figure 8:** Case study using our FANcY implementation on a Tofino switch.
   This is the only part of the evaluation that is not done through software
   simulations, and thus it requires special hardware. See more information
   [below](#running-tofino-case-study).
9. **Figure 11a:** Comparison of eight different hash-based trees for a 10-entry
   failure. The plot shows detection speed vs TPR and detectability vs False
   Positives.
10. **Figure 11b:** Comparison of eight different hash-based trees for a 50-entry
   failure. The plot shows detection speed vs TPR and detectability vs False
   Positives.

### Important Notes :warning:

Running all the different simulations requires quite a lot of computing power.
For the evaluation, we used a server with 64 cores and 256GB of ram, and it still
took more than one week to complete.

To make the whole process easier, we have prepared the following:

- We provide a `tar.gz` with the needed inputs for the simulations. You can
  [download here](https://polybox.ethz.ch/index.php/s/w3To3lCCnwIPDlz),
  otherwise if you use the VM you will find them at
   `~/fancy/fancy_sigcomm_inputs/`. For more details about the inputs, see
   [INPUTS.md](./INPUTS.md). We recommend you to directly use them. 
- We allow the `run_all.py` script to be run with two different modes `ALL` or
  `FAST`. If you select `ALL`, we run the same amount of iterations as described
  in the paper, however, simulations will take ~1 week with 64 cores (without
  using a VM). To speed up things, you can use `FAST` option to reduce the run
  time down to 1.5 days (with 64 cores). Keep in mind slightly affect some
  results.
- We also have added all the **pre-computed** data ready to be plotted. For
  that, we provide the pre-computed data for both `ALL` and `FAST` runs. See
  [plotting with precomputed data](#plotting-using-the-precomputed-data).
- We provide three scripts to automate the entire evaluation: `run_all.py`,
  `precompute_all` and `plot_all.py`.

### Running Simulations and Precomputing Data

In this section, we explain how to run all the needed simulations and parse
the results such that they can be easily plotted. 

If you are not using the VM, before starting, make sure you have
[downloaded](INPUTS.md#download-and-untar-inputs) and unzipped the simulation
inputs. Please, for simplicity place them at `~/fancy/fancy_sigcomm_inputs/`.

Before starting, and even if you are using the VM, make sure you are using the
latest version of the code:
```
# update main code base
cd ~/fancy/fancy-code/
git pull
# update simulation code.
cd simulation
git pull origin master
```

Now you are ready to start running the simulations:

1. The first thing you have to do is to run the `run_all.py` script. Also, this
   is the longest command of all the evaluations. With the `FAST` flag, it takes
   around 1.5 days with 64 cores. Thus, make sure you run this command using a
   `tmux` terminal such that it keeps running even if you close the terminal. 

   ```
   cd ~/fancy/fancy-code/eval_sigcomm2022/
   python3 scripts/run_all.py --cmds_dir cmds_fast --input_dir ~/fancy/fancy_sigcomm_inputs/ --output_dir ~/fancy/fancy_sigcomm_outputs/ --run_type FAST --ns3_path ~/fancy/<fancy-code>/simulation/ --cpus <number cpus>
   ```

   `run_all.py` command does two things: 
   - It first generates all the different `ns3`
   simulation runs and stores them at `cmds_fast/all_cmds.txt`. This file
   contains all the individual simulations and parameters! (165254 different runs for
   the `FAST` mode).
      ```
      wc all_cmds.txt
      165254   6114458 159880994 all_cmds.txt
      ```
   - Second, once it has computed the `all_cmds.txt` file, it then runs them in parallel using the number of cores you have selected above.

   :warning: Note that our `ns3` code is very verbose. You can hide the window where these simulations are running. :warning:

2. When finished, you should see the `~/fancy/fancy_sigcomm_outputs/` directory with the following folders:
   ```
   ls ~/fancy/fancy_sigcomm_outputs/
   eval_caida  eval_comparison  eval_dedicated  eval_uniform  eval_zooming_1  eval_zooming_100
   ```

   We can now parse all the outputs and pre-compute some processed data for our plotting scripts. For that you can run:

   ```
   cd ~/fancy/fancy-code/eval_sigcomm2022/
   python3 scripts/precompute_all.py --input_dir ~/fancy/fancy_sigcomm_outputs/ --data_inputs ~/fancy/fancy_sigcomm_inputs/ --output_dir ~/fancy/fancy_sigcomm_precomputed_inputs_fast/
   ```

   At this point, you will have all the needed results to generate plots and
   tables for most of the evaluation. However, to have `figure 8` you will have
   to run the Tofino experiments, see next section. Of course, you can skip that
   part and jump directly to the [ploting](#plotting-the-final-results) section.

### Running Tofino Case Study

To get the data to plot `figure 8` you will need to follow the [Tofino section
instructions](../tofino/). 

Once you have finished the experiments, create a folder named `eval_tofino` and
place it in the precomputed folder. If we use the one from above, that would be
inside `~/fancy/fancy_sigcomm_precomputed_inputs_fast/`. Copy the two folders
(`zooming_outputs` and `dedicated_outptus`) that you have generated during the
Tofino experiments. With that, the plotting script should handle the rest.

### Plotting the final results

To plot the results (using the precomputed dir we generated above), run:

```
cd ~/fancy/fancy-code/eval_sigcomm2022/
python3 ./scripts/plot_all.py --output_dir <name_output_dir> --input_dir ~/fancy/fancy_sigcomm_precomputed_inputs_fast/
```

At `output_dir` you will find the following:
-  All the paper plots with the form:`figureX.pdf`.
- `table3.txt` and `table3_reduced.txt`. To match with paper `table3` look at the section `Average of all traces` in the file `table3_reduced.txt`.
- `uniform_random_drops.txt` with the results of the uniform random drops experiments for section 5.1.3.

:bulb: **Important:** 

For the paper plots, I am using some special font that comes
with the `science` package. When plotting with `Ubuntu`, the following warning appears:
```
findfont: Font family ['serif'] not found. Falling back to DejaVu Sans.
```
This might affect a bit how some legends are placed, but the content of the plot
remains unaffected. When plotting with `Mac OS`, that does not happen.


#### Differences between `ALL` and `FAST` runs.

In order to run the experiments faster, we can select the `FAST` option, which
will instruct the script to remove some of the most CPU-intensive simulations.
However, that has the following implications:
- Figure 7b is missing the two upper rows. In any case, they are not very
  important since the TPR is always 1. This reduces the runtime by ~48-60h.
- Table 3 is run with three times fewer runs. Thus results might vary a bit. This reduced runtime by ~40h.
- Figure 11a/b is run with half the runs. Thus results might vary a bit. This reduced runtime by 4h.

#### Plotting using the precomputed data

We have prepared precomputed data that be directly plotted. We provide
pre-computed data for both `ALL` and `FAST` runs. To get it you can download and
untar it anywhere.

```
wget https://polybox.ethz.ch/index.php/s/yIpkLch0tmDxrVE/download -O precomputed_inputs.tar.gz
tar -xvf precomputed_inputs.tar.gz
```

After, you will find two folders: `precompute_inputs` (`ALL`) and
`precompute_inputs_fast` (`FAST`). Now you can directly generate plots from
them.

Generate the plots:
```
cd ~/fancy/<fancy-code>/eval_sigcomm2022/
python3 ./scripts/plot_all.py --output_dir plot_all/ --input_dir precomputed_inputs/
python3 ./scripts/plot_all.py --output_dir plot_fast/ --input_dir precomputed_inputs_fast/
```


