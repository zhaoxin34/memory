#!/bin/bash

INPUT=$(cat)
COMMAND=$(echo $INPUT | jq -r '.tool_input.command')
DESCRIPTION=$(echo $INPUT | jq -r '.tool_input.description')

TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
echo "[$TIMESTAMP] - $COMMAND - $DESCRIPTION" >> /tmp/bash-command-log.txt
