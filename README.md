# pygithub-labeler
Magically (and with the power of regular expressions) attach labels to your github repository issues.

http://slowbackspace.github.io/pygithub-labeler/

**Webhook Setup:**  
Webhooks allow you to build or set up integrations which subscribe to certain events on GitHub.com. When one of those events is triggered, Github will send a HTTP POST payload to the webhook's configured URL.

Github
- Go to you repository's settings -> Webhooks -> Add webhook  
- In the Payload URL field, write your-domain/hook
- Select Content Type application/json
- In the Secret field, write a secure random string
- Select events that will trigger this webhook. pygithub-labeler supports Issues, Issue comment and Pull request events.
- Click on "Add webhook"

pygithub-labeler
- Put your secret string into the env variable called "webhook_token"
- Start a web server via `python3 run.py web` or `./start_gunicorn.sh` 
  
For more information about webhooks visit <a href="https://developer.github.com/webhooks/">https://developer.github.com/webhooks/</a><br>

**Env variables:**  
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
