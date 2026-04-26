import pytest
from wsnsim.aggregation import PassthroughStrategy, TreeDeltaAvgStrategy

def test_passthrough_strategy():
    strategy = PassthroughStrategy()
    assert strategy.process_data(10.5) == 10.5
    assert strategy.process_data(20.0) == 20.0

def test_tree_delta_avg_strategy_windowing():
    # Window size 3
    strategy = TreeDeltaAvgStrategy(window_size=3)
    
    # First 2 points: no transmission
    assert strategy.process_data(10.0) is None
    assert strategy.process_data(12.0) is None
    
    # 3rd point: (10+12+14)/3 = 12.0. First transmission is raw.
    result1 = strategy.process_data(14.0)
    assert result1 == 12.0
    
    # Next window: (15+15+15)/3 = 15.0. Delta from 12.0 is 3.0.
    strategy.process_data(15.0)
    strategy.process_data(15.0)
    result2 = strategy.process_data(15.0)
    assert result2 == 3.0
    
    # Next window: (10+10+10)/3 = 10.0. Delta from 15.0 is -5.0.
    strategy.process_data(10.0)
    strategy.process_data(10.0)
    result3 = strategy.process_data(10.0)
    assert result3 == -5.0

def test_tree_delta_avg_threshold():
    # Window size 2, Threshold 1.0
    strategy = TreeDeltaAvgStrategy(window_size=2, threshold=1.0)
    
    # 1. First transmission (always sent)
    strategy.process_data(10.0)
    assert strategy.process_data(10.0) == 10.0 # Avg=10.0
    
    # 2. Small change: (10.2 + 10.4)/2 = 10.3. Delta = 0.3. 0.3 < 1.0 -> No send.
    strategy.process_data(10.2)
    assert strategy.process_data(10.4) is None
    
    # 3. Another small change: (10.5 + 10.5)/2 = 10.5. 
    # Delta from last SENT (10.0) is 0.5. 0.5 < 1.0 -> No send.
    strategy.process_data(10.5)
    assert strategy.process_data(10.5) is None
    
    # 4. Large change: (12.0 + 12.0)/2 = 12.0.
    # Delta from last SENT (10.0) is 2.0. 2.0 >= 1.0 -> Send.
    strategy.process_data(12.0)
    assert strategy.process_data(12.0) == 2.0

def test_tree_delta_avg_reset():
    strategy = TreeDeltaAvgStrategy(window_size=2)
    strategy.process_data(10.0)
    strategy.reset()
    # After reset, we need 2 more points
    assert strategy.process_data(20.0) is None
    assert strategy.process_data(30.0) == 25.0 # (20+30)/2
