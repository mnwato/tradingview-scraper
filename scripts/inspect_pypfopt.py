import inspect

import pypfopt
from pypfopt import HRPOpt

print(f"pypfopt version: {pypfopt.__version__}")
print(f"HRPOpt.optimize signature: {inspect.signature(HRPOpt.optimize)}")
