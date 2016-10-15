# pygithub-labeler
Magically (and with the power of regular expressions) attach labels to your github repository issues.

http://slowbackspace.github.io/pygithub-labeler/

Env variables:

PORT - port of the web server

DEBUG - Enable/disable debug mode (true/false)

webhook_token - Secret token for a webhook

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
