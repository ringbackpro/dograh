"""A single-source local database for recurring VA budget reports.

Replaces a chain of linked Excel workbooks with: files in, one SQLite database
out, data-quality checks on every load, and a stable set of views for Power BI.

Stdlib only -- no pip install, which matters on a locked-down workstation.
"""

__version__ = "0.1.0"
