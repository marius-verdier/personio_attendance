#!/bin/bash

set -e

# Check if 'jq' is installed
if ! command -v jq &> /dev/null; then
    echo "jq is required but not installed. Please install jq to proceed."
    exit 1
fi

# Parameters
EMAIL=""
PASSWORD=""
USER_AGENT=""
# the employee id can be found in the URL when you are logged in and you go to the time tracking page
EMPLOYEE_ID=
BASE_URL=""

TODAY=$(date +%Y-%m-%d)

DAY_OF_WEEK=$(date +%u)  # 1 (Monday) to 7 (Sunday)
if [ "$DAY_OF_WEEK" -ge 6 ]; then
    echo "Today is a weekend. Exiting."
    exit 0
fi

# Temporary files for storing cookies and headers
COOKIE_FILE=$(mktemp)
HEADER_FILE=$(mktemp)

HTML_CONTENT=$(curl --silent --location "https://$BASE_URL/login/index" \
    --header "User-Agent: $USER_AGENT" \
    --form "email=${EMAIL}" \
    --form "password=${PASSWORD}" \
    --cookie-jar "$COOKIE_FILE" \
    --dump-header "$HEADER_FILE")

if echo "$HTML_CONTENT" | grep -q "For security reasons you're required to enter the token"; then
    TOKEN=$(echo "$HTML_CONTENT" | grep -oP 'name="_token"\s+value="\K[^"]+')
    
    echo "Veuillez entrer le token que vous avez reçu par email :"
    read -r USER_TOKEN

    AUTH_RESPONSE=$(curl --silent --location "https://$BASE_URL/login/token-auth" \
        --header "User-Agent: $USER_AGENT" \
        --form "token=${USER_TOKEN}" \
        --form "_token=${TOKEN}" \
        --cookie "$COOKIE_FILE" \
        --cookie-jar "$COOKIE_FILE" \
        --dump-header "$HEADER_FILE")
fi

XSRF_TOKEN=$(grep 'XSRF-TOKEN' "$COOKIE_FILE" | awk '{print $7}')
COOKIES=$(awk '{print $6"="$7}' "$COOKIE_FILE" | tr '\n' ';' | sed 's/;$//')

# On MacOS, replace by
# START_TS=$(date -j -f "%Y-%m-%d %H:%M:%S" "$TODAY 00:00:00" "+%s")
# END_TS=$(date -j -f "%Y-%m-%d %H:%M:%S" "$TODAY 23:59:59" "+%s")
START_TS=$(date -d "$TODAY 00:00:00" +%s)
END_TS=$(date -d "$TODAY 23:59:59" +%s)

HOLIDAY_RESPONSE=$(curl --silent --location "https://$BASE_URL/time-off/holidays/${EMPLOYEE_ID}?start=${START_TS}&end=${END_TS}" \
    --header "User-Agent: $USER_AGENT" \
    --header "x-csrf-token: $XSRF_TOKEN" \
    --header "x-xsrf-token: $XSRF_TOKEN" \
    --header 'Accept: application/json, text/plain, */*' \
    --header "Cookie: $COOKIES")

HOLIDAY_TODAY=$(echo "$HOLIDAY_RESPONSE" | jq --arg date "$TODAY" '.[] | select(.start == $date)')

if [ -n "$HOLIDAY_TODAY" ]; then
    echo "Today is a holiday. Exiting."
    exit 0
fi

ABSENCE_RESPONSE=$(curl --silent --location "https://$BASE_URL/absence-periods?employee_ids=${EMPLOYEE_ID}&absence_type_ids=&start=${TODAY}&end=${TODAY}" \
    --header "User-Agent: $USER_AGENT" \
    --header "x-csrf-token: $XSRF_TOKEN" \
    --header "x-xsrf-token: $XSRF_TOKEN" \
    --header 'Accept: application/json, text/plain, */*' \
    --header "Cookie: $COOKIES")

ABSENCE_DATA=$(echo "$ABSENCE_RESPONSE" | jq '.data')
ABSENCE_COUNT=$(echo "$ABSENCE_DATA" | jq 'length')

if [ "$ABSENCE_COUNT" -eq 0 ]; then
    :
else
    ABSENCE_FULL_DAY=false
    ABSENCE_MORNING=false
    ABSENCE_AFTERNOON=false

    for (( i=0; i<ABSENCE_COUNT; i++ )); do
        ABSENCE=$(echo "$ABSENCE_DATA" | jq ".[$i]")
        START_DATE=$(echo "$ABSENCE" | jq -r '.attributes.start' | cut -d'T' -f1)
        END_DATE=$(echo "$ABSENCE" | jq -r '.attributes.end' | cut -d'T' -f1)

        TYPE=$(echo "$ABSENCE" | jq -r '.attributes.absence_type_id')

        if [ "$TYPE" == "2664556" ]; then
            echo "Today is a home working day. Full clocking."
            break
        fi
        
        HALF_DAY_START=$(echo "$ABSENCE" | jq -r '.attributes.half_day_start')
        HALF_DAY_END=$(echo "$ABSENCE" | jq -r '.attributes.half_day_end')
        
        if [ "$START_DATE" == "$TODAY" ] || [ "$END_DATE" == "$TODAY" ] || { [ "$START_DATE" \< "$TODAY" ] && [ "$END_DATE" \> "$TODAY" ]; }; then
            if [ "$HALF_DAY_START" == "false" ] && [ "$HALF_DAY_END" == "false" ]; then
                ABSENCE_FULL_DAY=true
            elif [ "$HALF_DAY_START" == "true" ] && [ "$HALF_DAY_END" == "false" ]; then
                ABSENCE_MORNING=true
            elif [ "$HALF_DAY_START" == "false" ] && [ "$HALF_DAY_END" == "true" ]; then
                ABSENCE_AFTERNOON=true
            else
                ABSENCE_FULL_DAY=true
            fi
        fi
    done

    if [ "$ABSENCE_FULL_DAY" == "true" ]; then
        echo "Today is a full day absence. Exiting."
        exit 0
    elif [ "$ABSENCE_MORNING" == "true" ] && [ "$ABSENCE_AFTERNOON" == "true" ]; then
        echo "Today is a full day absence (both half days). Exiting."
        exit 0
    elif [ "$ABSENCE_MORNING" == "true" ]; then
        JSON_DATA=$(cat <<EOF
{
    "dates": ["$TODAY"],
    "employee_id": $EMPLOYEE_ID,
    "periods": [
        {"start": "14:00", "end": "18:00", "type": "work", "comment": null, "project_id": null}
    ]
}
EOF
)
    elif [ "$ABSENCE_AFTERNOON" == "true" ]; then
        JSON_DATA=$(cat <<EOF
{
    "dates": ["$TODAY"],
    "employee_id": $EMPLOYEE_ID,
    "periods": [
        {"start": "09:00", "end": "13:00", "type": "work", "comment": null, "project_id": null}
    ]
}
EOF
)
    else
        :
    fi
fi

if [ -z "$JSON_DATA" ]; then
    START_MINUTE=$((RANDOM % 10))
    START_TIME=$(printf "09:%02d" $START_MINUTE)
    END_TIME=$(printf "18:%02d" $START_MINUTE)

    JSON_DATA=$(cat <<EOF
{
    "dates": ["$TODAY"],
    "employee_id": $EMPLOYEE_ID,
    "periods": [
        {"start": "$START_TIME", "end": "13:00", "type": "work", "comment": null, "project_id": null},
        {"start": "13:00", "end": "14:00", "type": "break", "comment": null, "project_id": null},
        {"start": "14:00", "end": "$END_TIME", "type": "work", "comment": null, "project_id": null}
    ]
}
EOF
)
fi

curl --silent --location --request PUT "https://$BASE_URL/svc/attendance-api/v1/days" \
    --header "User-Agent: $USER_AGENT" \
    --header "x-csrf-token: $XSRF_TOKEN" \
    --header "x-xsrf-token: $XSRF_TOKEN" \
    --header 'Accept: application/json, text/plain, */*' \
    --header 'Content-Type: application/json' \
    --header "Cookie: $COOKIES" \
    --data "$JSON_DATA" > /dev/null

rm "$COOKIE_FILE" "$HEADER_FILE"