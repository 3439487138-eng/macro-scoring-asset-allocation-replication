import numpy as np
import pandas as pd
import pytest
from macro_allocation.production_backtest import run_backtest
from macro_allocation.errors import DataValidationError

def inputs():
    idx=pd.date_range("2020-01-31",periods=4,freq="ME")
    pos=pd.DataFrame({"CREDIT":[1,-1,1,1]},index=idx)
    ret=pd.DataFrame({"CREDIT":[.01,.02,.03,.04]},index=idx)
    cash=pd.Series([.001]*4,index=idx)
    return idx,pos,ret,cash

def test_lag_cost_cash_and_compounding_contract():
    idx,pos,ret,cash=inputs(); result=run_backtest(pos,ret,cash,{"CREDIT":1},10,"2020-02-29")
    assert result.allocations.CREDIT.tolist()==[1,-1,1]
    assert (result.rebalance.signal_date < result.rebalance.execution_date).all()
    assert np.allclose(result.monthly.transaction_cost,result.monthly.turnover*.001)
    assert np.isclose(result.monthly.iloc[0].gross_return,.02)

def test_key_mismatch_is_fatal():
    idx,pos,ret,cash=inputs()
    with pytest.raises(DataValidationError,match="keys must match"):
        run_backtest(pos,ret,cash,{"SHORT_BOND":1},10,"2020-02-29")

def test_missing_return_is_never_zero():
    idx,pos,ret,cash=inputs(); ret.iloc[1,0]=np.nan
    with pytest.raises(DataValidationError,match="cannot be treated as zero"):
        run_backtest(pos,ret,cash,{"CREDIT":1},10,"2020-02-29")
