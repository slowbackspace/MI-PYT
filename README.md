# pygithub-labeler
Magically (and with the power of regular expressions) attach labels to your github repository issues.

https://github.com/slowbackspace/pygithub-labeler/

```
Usage: run.py [OPTIONS] COMMAND [ARGS]...

Options:
  --authconfig TEXT   Configuration file. Default auth.cfg
  --repo TEXT         Repository in 'owner/name' format. Default
                      slowbackspace/testrepo
  --scope TEXT        Scope - issue_body, issue_comments, pull_requests, all.
                      Default all
  --rules TEXT        Rules configuration file
  --interval INTEGER  Interval [seconds]. Default 5
  --label TEXT        Fallback label. Default wonfix
  --help              Show this message and exit

Commands:
  console  Run the cli app
  web      Run the web app
```

## Web
Live preview: http://labeler.cftest.homeatcloud.cz

Github webhook: http://labeler.cftest.homeatcloud.cz/hook
