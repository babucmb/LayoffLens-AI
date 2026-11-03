# Model and evaluation

The numeric engine is intentionally explainable: weighted pipeline is the sum of probability-weighted project value multiplied by conversion; capacity gap is adjusted demand minus capacity minus mobility offset. Confidence is a bounded heuristic reflecting assumption sensitivity, not a calibrated probability.

The evaluation view reports a synthetic forecast/actual series, MAE, and WAPE. It also names what went wrong. Controlled learning means updating data and evaluating historical windows; it does not update model weights after every event. Promotion requires backtesting and human approval.
