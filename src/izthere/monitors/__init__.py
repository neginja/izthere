# force initialization of subclasses before from_config
from izthere.monitors.html_word_monitor import (
    HtmlWordMonitor,  # noqa: F401  # pyright: ignore[reportUnusedImport]
)
from izthere.monitors.json_parser_monitor import (
    JSONParserMonitor,  # noqa: F401  # pyright: ignore[reportUnusedImport]
)
from izthere.monitors.xpath_word_monitor import (
    XpathWordMonitor,  # noqa: F401  # pyright: ignore[reportUnusedImport]
)
