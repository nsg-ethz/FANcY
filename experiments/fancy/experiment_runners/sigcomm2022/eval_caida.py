
# full system enabled hybrid mode.
fixed_parameters = \
    [
        {"NumTopEntriesSystem": 500, "TreeDepth": 3, "LayerSplit": 2,
            "CounterWidth": 190, "TreeEnabled": True},
    ]


# used traces we fail 1 by 1 the top 10k prefixes in those 3 traces.
# For nyc2018A we only fail 6.5K since there is no more.
caida_traces = ['equinix-chicago.dirB.20140619',
                'equinix-nyc.dirA.20180419', 'equinix-nyc.dirB.20180816']


# 3 runs, more is not needed since we do 500K experiments already.
# with 64 cores this took 63H, 33h with 128 cores.
variable_parameters_caida_all = {
    "Traces": caida_traces,
    "MaxCounterCollisions": [2],
    "SendDuration": [30],
    "ProbingTimeZoomingMs": [200],
    "ProbingTimeTopEntriesMs": [50],
    "SwitchDelay": [10000],
    "Pipeline": ["true"],
    "PipelineBoost": ["true"],
    "CostType": [1],
    "FailDropRate": [1, 0.75, 0.5, 0.1, 0.01, 0.001],
    "Seed": range(1, 4),
    "NumDrops": [1],
    "NumTopEntriesTraffic": [100000],
    "TraceSlice": [0]
}

# only one seed per prefix. This should reduce runtime 3 times.
# 63H to 21H. This can not be further reduced I guess.
variable_parameters_caida_fast = {
    "Traces": caida_traces,
    "MaxCounterCollisions": [2],
    "SendDuration": [30],
    "ProbingTimeZoomingMs": [200],
    "ProbingTimeTopEntriesMs": [50],
    "SwitchDelay": [10000],
    "Pipeline": ["true"],
    "PipelineBoost": ["true"],
    "CostType": [1],
    "FailDropRate": [1, 0.75, 0.5, 0.1, 0.01, 0.001],
    "Seed": range(1, 2),
    "NumDrops": [1],
    "NumTopEntriesTraffic": [100000],
    "TraceSlice": [0]
}
