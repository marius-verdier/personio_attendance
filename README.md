# Automated Personio clock

Side project to learn how to use Scrapy in a simple case.

## Prerequisites

- Python 3.x
- git (to clone the repository)

## Setup Instructions

### On Unix/Linux/MacOS

```bash
git clone git@github.com:marius-verdier/personio_attendance.git
cd personio_attendance
chmod +x setup.sh
./setup.sh
```

Once the setup is done, don't forget to go in the virtual environment by running
```
source .venv/bin/activate
```

## Configuration

Once you cloned the repo, you'll have to create a `.env` file in the root folder. The environment file (see `.env.template`) should contain the following informations :

```
# for example, if your personio url is https://company.personio.de/, the following will be
CREDS_EMAIL=mail@mail.com
CREDS_PASS=password
BASE_URL=company.personio.de

# NON_WORKING_DAYS should contain week days on which the clock-in/out will should not be make, for example week-end.
# NON_WORKING_TRIGGERS should contain triggers display in the day cell in personio meaning the day is a non-working day for you. I
# suggest you refer to your personio interface (the match should be perfect)
NON_WORKING_DAYS=saturday,sunday,thursday
NON_WORKING_TRIGGERS=Paid Leave,Unpaid Leave,Holiday,Paid holidays

# The following elements refer to the shift hours you want to make every day on personio
SHIFT_START=09:00
SHIFT_END=18:00
BREAK_START=13:00
BREAK_END=14:00
```

## Usage CLI

Every attendance action is available using some commands instead of going on the platform :
- To clock in (at the moment you run the command) : `scrapy crawl attendance -a action=start`
- To take a break (at the moment you run the command) : `scrapy crawl attendance -a action=break`
- To end a break (at the moment you run the command) : `scrapy crawl attendance -a action=stop_break`
- To clock out (at the moment you run the command) : `scrapy crawl attendance -a action=stop`


## Usage for a full attendance record 

To register a full attendance record for the current day, using the day verification and the shift hours, after filling the environment file, run :

`scrapy crawl full_attendance`

todo : 
- random hours