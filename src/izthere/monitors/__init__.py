# force initialization of subclasses before from_config
from .ashby_board_watcher import (
    AshbyBoardMonitor,  # noqa: F401  # pyright: ignore[reportUnusedImport]
)
from .html_word_monitor import (
    HtmlWordMonitor,  # noqa: F401  # pyright: ignore[reportUnusedImport]
)
from .xpath_word_monitor import (
    XpathWordMonitor,  # noqa: F401  # pyright: ignore[reportUnusedImport]
)
