"""Analysis engine: pure measurement, no UI code, no advice.

Everything here works on linear data. The display stretch never touches it.
"""

from advastro.engine.metrics import SubMetrics, measure_frame
from advastro.engine.session import SessionSummary, analyze_paths, summarize

__all__ = ["SubMetrics", "measure_frame", "SessionSummary", "analyze_paths", "summarize"]
