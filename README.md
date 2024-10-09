# Automated Personio clock

Side project to learn how to use Scrapy in a simple case.

## Usage

To use this tool, please clone the repo, then create the environment file, containing 

```
CREDS_EMAIL=
CREDS_PASS=
BASE_URL=
```
`BASE_URL` contains the domain of your Personio platform, without https://

To manage your Personio attendance, please follow the instructions below :
- To clock in : `scrapy crawl attendance -a action=start`
- To take a break : `scrapy crawl attendance -a action=break`
- To end a break : `scrapy crawl attendance -a action=stop_break`
- To clock out : `scrapy crawl attendance -a action=stop`