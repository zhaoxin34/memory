!/bin/bash
COMMAND=$(jq -r '.tool_input.command')

echo "$COMMAND" >> /tmp/bash-command-log.txt
