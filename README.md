# IzThere

A tiny monnitoring/notification service for the web.

## Example

For example currently I am interested in a new job in a privacy focused company (say DDG) and I also want to buy Da Vinci Resolve Studio edition for cheap, here would be my setup (`config.yaml`)

```yaml
monitors:
  - question: Iz There a video editing bundle for purchase?
    type: html_word
    url: "https://www.humblebundle.com/software"
    keywords:
      - "video editing"
      - "film making"
      - "da vinci"
    case_sensitive: false
    timeout_seconds: 15
    schedule: "0 12 * * *" # once a day at 12
    notifiers:
      - telegram_main
  - question: Iz There some engineering jobs at DuckDuckGo for my location
    type: ashby_board
    url: "https://jobs.ashbyhq.com/duck-duck-go"
    location_name: "<your country>"
    remote_only: true
    keywords:
      - engineer
    case_sensitive: false
    timeout_seconds: 15
    schedule: "0 12 * * *" # once a day at 12
    notifiers:
      - telegram_main

notifiers:
  - name: telegram_main
    type: telegram
    bot_token: "<YOUR_BOT_TOKEN>"
    chat_id: "<CHANNEL_OR_GROUP_ID>"
```

The above monitors will check everyday the DDG ashby board and humble bundle software page and send me a notification via telegram.

Monitors and Notifiers implement an interface, so you can extend it to anything you need.

## Available monitors and notifiers

Monitors:

1. `html_word` look for some keywords are found inside the visible content of a web page
2. `xpath_word` look for some keywords are found inside a specific section (`xpath` and children) of a web page
3. `ashby_board` look for jobs with keywords in their title available in a given location on an Ashby board

Notifiers:

1. `telegram`: send results to a telegram conversation or group


## Install

You'll need `uv`

```console
uv sync
```

then for use of JS when loading web pages

```console
uv run python -m playwright install
```

Finally

```console
uv run izthere
```

and you can detach if you want to let it run in the background