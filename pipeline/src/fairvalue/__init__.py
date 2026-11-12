"""FairValue Football pipeline.

Offline, batch pipeline: frozen raw sources -> staging -> as-of features ->
models (profiles, performance-implied value, expected fee) -> exports for the
web app. See docs/PRODUCT_SPEC.md section 6-7.
"""

__version__ = "0.1.0"
