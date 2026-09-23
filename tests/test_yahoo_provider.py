import pytest
from macro_allocation.yahoo_provider import parse_chart_response
from macro_allocation.errors import DataValidationError

def test_adjusted_close_is_required():
    payload={"chart":{"result":[{"timestamp":[1]*100,"indicators":{"quote":[{}]}}],"error":None}}
    with pytest.raises(DataValidationError,match="adjusted close"):
        parse_chart_response("X",payload)
