# usually system design

# this is special because we are cherry picking the size of the prefixes.
# this is used for the heat map plot.

# tree enabled
fixed_parameters = \
    [
        {"NumTopEntriesSystem": 0, "TreeDepth": 3, "LayerSplit": 2,
            "CounterWidth": 190, "TreeEnabled": True},
    ]


# for plot 6, 7a
# runtime 1h
variable_parameters_zooming_1_all = {
    "MaxCounterCollisions": [2],
    "SendDuration": [30],
    "ProbingTimeZoomingMs": [10, 50, 100, 200],
    "ProbingTimeTopEntriesMs": [50],
    "SwitchDelay": [10000],
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


# ALL
# all things
# for plot 7b
# runtime
# 50h because of the top processes
variable_parameters_zooming_100_all = {
    "MaxCounterCollisions": [2],
    "SendDuration": [30],
    "ProbingTimeZoomingMs": [200],
    "ProbingTimeTopEntriesMs": [50],
    "SwitchDelay": [10000],
    "Pipeline": ["true"],
    "PipelineBoost": ["true"],
    "CostType": [1],
    "FailDropRate": [1, 0.75, 0.5, 0.1, 0.01, 0.001],
    "Seed": range(1, 11),
    "SyntheticNumPrefixes": [100],
    "SendRate|FlowsPerSec": [("4Kbps", 1), ("8Kbps", 1), ("8Kbps", 2), ("25Kbps", 2),
                             ("25Kbps", 5), ("50kbps", 5), ("50Kbps", 10), ("100Kbps", 10),
                             ("100Kbps", 25), ("500Kbps", 25), ("500Kbps", 50), ("1Mbps", 50),
                             ("1Mbps", 100), ("10Mbps", 100), ("10Mbps", 150), ("50Mbps", 150),
                             ("100Mbps", 200), ("200Mbps", 200)]
}

# FAST
# to make the experiments faster we remove the top 2 rows for the 100 prefixes
# for plot 7b
# runtime less than 1 day.
variable_parameters_zooming_100_fast = {
    "MaxCounterCollisions": [2],
    "SendDuration": [30],
    "ProbingTimeZoomingMs": [200],
    "ProbingTimeTopEntriesMs": [50],
    "SwitchDelay": [10000],
    "Pipeline": ["true"],
    "PipelineBoost": ["true"],
    "CostType": [1],
    "FailDropRate": [1, 0.75, 0.5, 0.1, 0.01, 0.001],
    "Seed": range(1, 11),
    "SyntheticNumPrefixes": [100],
    "SendRate|FlowsPerSec": [("4Kbps", 1), ("8Kbps", 1), ("8Kbps", 2), ("25Kbps", 2),
                             ("25Kbps", 5), ("50kbps", 5), ("50Kbps", 10), ("100Kbps", 10),
                             ("100Kbps", 25), ("500Kbps", 25), ("500Kbps", 50), ("1Mbps", 50),
                             ("1Mbps", 100), ("10Mbps", 100), ("10Mbps", 150), ("50Mbps", 150)]
}


# OLD FAST RUN
# we keep the size 1 the same since it is only 1h

# Reduce top 2 prefixes and seeds from 10 to 5
# variable_parameters_zooming_100_fast = {
#    "MaxCounterCollisions": [2],
#    "SendDuration": [30],
#    "ProbingTimeZoomingMs": [200],
#    "ProbingTimeTopEntriesMs": [50],
#    "SwitchDelay": [10000],
#    "Pipeline": ["true"],
#    "PipelineBoost": ["true"],
#    "CostType": [1],
#    "FailDropRate": [1, 0.75, 0.5, 0.1, 0.01, 0.001],
#    "Seed": range(1, 6),
#    "SyntheticNumPrefixes": [100],
#    "SendRate|FlowsPerSec": [("4Kbps", 1), ("8Kbps", 1), ("8Kbps", 2), ("25Kbps", 2),
#                             ("25Kbps", 5), ("50kbps", 5), ("50Kbps", 10), ("100Kbps", 10),
#                             ("100Kbps", 25), ("500Kbps", 25), ("500Kbps", 50), ("1Mbps", 50),
#                             ("1Mbps", 100), ("10Mbps", 100), ("10Mbps", 150), ("50Mbps", 150)]
# }


# in the past we did 50, 30, 10 runs. Now I am doing 10 of each.
# we need to do for different burst sizes
# "SyntheticNumPrefixes": [1, 10, 100], 1, 5, 10ms one day delay
# For burst 10 or 100
# variable_parameters = {
#    "MaxCounterCollisions": [2],
#    "SendDuration": [30],
#    "ProbingTimeZoomingMs": [10, 50, 100, 200],
#    "ProbingTimeTopEntriesMs": [50],
#    "SwitchDelay": [1000, 5000, 10000],
#    "Pipeline": ["true"],
#    "PipelineBoost": ["true"],
#    "CostType": [1],
#    "FailDropRate": [1, 0.75, 0.5, 0.1, 0.01, 0.001],
#    "Seed": range(1, 11),
#    "SyntheticNumPrefixes": [10],
#    "SendRate|FlowsPerSec": [("4Kbps", 1), ("8Kbps", 1), ("8Kbps", 2), ("25Kbps", 2),
#                ("25Kbps", 5), ("50kbps", 5), ("50Kbps", 10), ("100Kbps", 10),
#                ("100Kbps", 25), ("500Kbps", 25), ("500Kbps", 50), ("1Mbps", 50),
#                ("1Mbps", 100), ("10Mbps", 100), ("10Mbps", 150), ("50Mbps", 150),
#                ("100Mbps", 200), ("200Mbps", 200)]
# }
