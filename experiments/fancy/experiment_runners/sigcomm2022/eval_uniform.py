# usually system design

# Only tree enabled
fixed_parameters = \
    [
        {"NumTopEntriesSystem": 0, "TreeDepth": 3, "LayerSplit": 2,
            "CounterWidth": 190, "TreeEnabled": True},  # 1mb
    ]

# we set uniform threshold to ~50%> number of counters 190 -> 100
# 5 runs is enough, this does not change almost
# runtime ~1h 15min with 45 CPUS
# since runtime is ~1h we do not need faster runners.
variable_parameters_uniform_all = {
    "MaxCounterCollisions": [2],
    "SendDuration": [10],
    "ProbingTimeZoomingMs": [200],
    "ProbingTimeTopEntriesMs": [50],
    "SwitchDelay": [10000],
    "Pipeline": ["true"],
    "PipelineBoost": ["true"],
    "CostType": [1],
    "FailDropRate": [1, 0.75, 0.5, 0.1, 0.01, 0.001],
    "UniformLossThreshold": [100],
    "SyntheticNumPrefixes": [1000, 10000],
    "SendRate": ["10Gbps"],
    "FlowsPerSec": [5],
    "Seed": range(1, 6)
}

# What we say in the paper:
# In order to be realistic, we simulate a network with 100Gbps links, and
# assign traffic to entries mimicking Zipf distribution – i.e., mapping 10% of
# the traffic to 1,000-10,000 entries (as in the tail of a Zipf distribution).
# We then vary the packet loss rate per entry between 100% and 0.1%.

# paper run
# variable_parameters = {
#    "MaxCounterCollisions": [2],
#    "SendDuration": [10],
#    "ProbingTimeZoomingMs": [200],
#    "ProbingTimeTopEntriesMs": [50],
#    "SwitchDelay": [1000, 5000, 10000],
#    "Pipeline": ["true"],
#    "PipelineBoost": ["true"],
#    "CostType": [1],
#    "FailDropRate": [1, 0.75, 0.5, 0.1, 0.01, 0.001],
#    "UniformLossThreshold": [100],
#    "SyntheticNumPrefixes": [1000, 10000],
#    "SendRate": ["10Gbps"],
#    "FlowsPerSec": [5],
#    "Seed": range(1, 6)
# }
