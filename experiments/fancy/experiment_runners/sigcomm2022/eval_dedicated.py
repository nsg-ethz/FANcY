
# dedicated entries benchmark run inputs.

# system description: this is constant
fixed_parameters = \
    [
        {"NumTopEntriesSystem": 1, "TreeDepth": 3, "LayerSplit": 2,
            "CounterWidth": 190, "TreeEnabled": False},
    ]

# Full run 10ms inter switch delay and 50ms probing time.
# runtime 5min
variable_parameters_dedicated_all = {
    "MaxCounterCollisions": [2],
    "SendDuration": [30],
    "ProbingTimeZoomingMs": [100],  # does not matter
    "ProbingTimeTopEntriesMs": [50],
    "SwitchDelay": [10000],  # 10ms
    "Pipeline": ["true"],
    "PipelineBoost": ["true"],
    "CostType": [1],
    "FailDropRate": [1, 0.75, 0.5, 0.1, 0.01, 0.001],
    "Seed": range(1, 11),
    "SyntheticNumPrefixes": [1],
    "SendRate|FlowsPerSec": [("4Kbps", 1), ("8Kbps", 1), ("8Kbps", 2), ("25Kbps", 2),
                             ("25Kbps", 5), ("50kbps",
                                             5), ("50Kbps", 10), ("100Kbps", 10),
                             ("100Kbps", 25), ("500Kbps",
                                               25), ("500Kbps", 50), ("1Mbps", 50),
                             ("1Mbps", 100), ("10Mbps",
                                              100), ("10Mbps", 150), ("50Mbps", 150),
                             ("100Mbps", 200), ("500Mbps", 250)]
}


# all things with extra switch delays, not used for plots
# runtime ~20min
variable_parameters_dedicated_extra = {
    "MaxCounterCollisions": [2],
    "SendDuration": [30],
    "ProbingTimeZoomingMs": [100],
    "ProbingTimeTopEntriesMs": [10, 50, 100],
    "SwitchDelay": [1000, 5000, 10000],
    "Pipeline": ["true"],
    "PipelineBoost": ["true"],
    "CostType": [1],
    "FailDropRate": [1, 0.75, 0.5, 0.1, 0.01, 0.001],
    "Seed": range(1, 11),
    "SyntheticNumPrefixes": [1],
    "SendRate|FlowsPerSec": [("4Kbps", 1), ("8Kbps", 1), ("8Kbps", 2), ("25Kbps", 2),
                             ("25Kbps", 5), ("50kbps", 5), ("50Kbps", 10), ("100Kbps", 10),
                             ("100Kbps", 25), ("500Kbps", 25), ("500Kbps", 50), ("1Mbps", 50),
                             ("1Mbps", 100), ("10Mbps", 100), ("10Mbps", 150), ("50Mbps", 150),
                             ("100Mbps", 200), ("500Mbps", 250)]
}
