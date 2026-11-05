#!/bin/bash
# The Mac fine-tune now lives in train_on_mac.sh: every conversation, the same honesty check as the cloud run, and the
# result installed as Luma's own brain (Settings > Brain). This name still works.
exec bash "$(dirname "$0")/train_on_mac.sh" "$@"
