

# all different systems we compare
fixed_parameters = \
    [
        {"NumTopEntriesSystem": 0, "TreeDepth": 3, "LayerSplit": 3,
            "CounterWidth": 205, "TreeEnabled": True},   # 1mb / 8.6M
        {"NumTopEntriesSystem": 0, "TreeDepth": 3, "LayerSplit": 2,
            "CounterWidth": 190, "TreeEnabled": True},   # 500kb 6.9M
        {"NumTopEntriesSystem": 0, "TreeDepth": 3, "LayerSplit": 3,
            "CounterWidth": 100, "TreeEnabled": True},   # 500kb 1M
        {"NumTopEntriesSystem": 0, "TreeDepth": 4, "LayerSplit": 3,
            "CounterWidth": 32, "TreeEnabled": True},    # 500kb 1M
        {"NumTopEntriesSystem": 0, "TreeDepth": 3, "LayerSplit": 2,
            "CounterWidth": 100, "TreeEnabled": True},   # 250 kb 1M
        {"NumTopEntriesSystem": 0, "TreeDepth": 4, "LayerSplit": 2,
            "CounterWidth": 44, "TreeEnabled": True},   # 250 kb 3.7M
        {"NumTopEntriesSystem": 0, "TreeDepth": 3, "LayerSplit": 1,
            "CounterWidth": 110, "TreeEnabled": True},  # 125 1.3M
        {"NumTopEntriesSystem": 0, "TreeDepth": 4, "LayerSplit": 2,
            "CounterWidth": 28, "TreeEnabled": True},   # 125 0.6MM
    ]

# Runtime: 64 cores 7-8h.
# zooming speed is estimated from what is best analyzing the traces.
variable_parameters_comparison_all = {
    "Traces": ['equinix-nyc.dirB.20190117'],
    "MaxCounterCollisions": [2],
    "SendDuration": [30],
    "ProbingTimeZoomingMs": ["estimate"],
    "ProbingTimeTopEntriesMs": [50],
    "Pipeline": ["true"],
    "PipelineBoost": ["true"],
    "CostType": [1],
    "NumTopEntriesTraffic": [1000000],
    "FailDropRate": [1],
    "NumTopFails": [10, 50],
    "TopFailType": ["Random"],
    "NumBottomFails": [0],
    "BottomFailType": ["Random"],
    "TraceSlice": [0],
    "Seed": list(range(1, 11))
}

# reduce seeds from 10 to 5, to reduce runtime by 2 ~3.5h with 64 cores
variable_parameters_comparison_fast = {
    "Traces": ['equinix-nyc.dirB.20190117'],
    "MaxCounterCollisions": [2],
    "SendDuration": [30],
    "ProbingTimeZoomingMs": ["estimate"],
    "ProbingTimeTopEntriesMs": [50],
    "Pipeline": ["true"],
    "PipelineBoost": ["true"],
    "CostType": [1],
    "NumTopEntriesTraffic": [1000000],
    "FailDropRate": [1],
    "NumTopFails": [10, 50],
    "TopFailType": ["Random"],
    "NumBottomFails": [0],
    "BottomFailType": ["Random"],
    "TraceSlice": [0],
    "Seed": list(range(1, 6))
}
