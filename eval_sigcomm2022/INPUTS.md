# Simulation Inputs

For some of the simulation experiments, we use traces from the [The CAIDA Anonymized Internet Traces](https://www.caida.org/catalog/datasets/passive_dataset_download/). In order to be able to download them, you need to request access to CAIDA. 

Since the processing we do is not really part of the evaluation of `Fancy`, and to make your life easier, we provide you with the exact set of 
data inputs we use for our simulations. You can download them [here](https://polybox.ethz.ch/index.php/s/w3To3lCCnwIPDlz) or if you use the provided VM, you will already find the inputs at `~/fancy/fancy_sigcomm_inputs/`.

To download the inputs from the terminal:
```
# to download
wget https://polybox.ethz.ch/index.php/s/w3To3lCCnwIPDlz/download -O fancy_sigcomm_inputs.tar.gz

# to uncompress
tar -xvf fancy_sigcomm_inputs.tar.gz
```

Inside the folder you will find the following folders. 

```
fancy_sigcomm_inputs
├── equinix-chicago.dirB.20140619
├── equinix-nyc.dirA.20180419
├── equinix-nyc.dirB.20180816
├── equinix-nyc.dirB.20190117
└── zooming_info
```

For each of the four caida traces there is some simple precomputed files: 

Global information computed over the entire 1h trace: 
1. `<trace_name>.top`: sorted list of all the /24 prefixes with the amount of total bytes sent in 1h and packets. 
2. `<trace_name>.capinfos`: capinfos of this trace
3. `<trace_name>.cdf`: bytes and packets cdf per prefix. 

Slice information. This contains trace information for a 30 second slice. You will just need the first slice number 0:
1. `<trace_name>_<slice_number>.bin`: compressed version of the pcap. It just keeps basic five tuple info and timestamp. 
2. `<trace_name>_<slice_number>.ts`: for each prefix is has all the timestamps for every packet sent. 
3. `<trace_name>_<slice_number>.cdf`: bytes and packets cdf per prefix.
4. `<trace_name>_<slice_number>.freq`: flows per second that are observed
5. `<trace_name>_<slice_number>.info`: timestamp start and end (real times from the trace)
6. `<trace_name>_<slice_number>.rtts`: All the RTTs we could infer from the trace, monitoring SYN and SYN ACKS. 
7. `<trace_name>_<slice_number>_rtt_cdfs.txt`: Compressed CDF of all the RTTs.
8. `<trace_name>_<slice_number>.top`: All prefixes sorted by bytes and packets. 
9. `<trace_name>_<slice_number>.dist`: for each prefix and for each flow: start, end, duration, size, and rtt. This is used to generate flows.

### Generating the inputs.

For a given 1h trace you can generate the input traces digests by using
`main_pcap_prefix_info` from
[`experiments/fancy/parse_traces/pcap_parse.py`](../experiments/fancy/parse_traces/pcap_parse.py).

Download the following traces 
`['equinix-chicago.dirB.20140619', 'equinix-nyc.dirA.20180419', 'equinix-nyc.dirB.20180816','equinix-nyc.dirB.20190117']`. And put them at `traces_path`.

Then run:

```
all_traces = [
    'equinix-chicago.dirB.20140619', 'equinix-nyc.dirA.20180419',
    'equinix-nyc.dirB.20180816', 'equinix-nyc.dirB.20190117']

main_pcap_prefix_info(
        traces_path, all_traces, slice_size=30, skip_after=30, slices=1,
        processes=1):
```