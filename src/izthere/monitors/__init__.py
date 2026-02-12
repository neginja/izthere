# force initialization of subclasses before from_config
from izthere.monitors.ashby_board_monitor import (
    AshbyBoardMonitor,  # noqa: F401  # pyright: ignore[reportUnusedImport]
)
from izthere.monitors.html_word_monitor import (
    HtmlWordMonitor,  # noqa: F401  # pyright: ignore[reportUnusedImport]
)
from izthere.monitors.xpath_word_monitor import (
    XpathWordMonitor,  # noqa: F401  # pyright: ignore[reportUnusedImport]
)
