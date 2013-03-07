#!/bin/bash

# This script is used to register InaSAFE translatable resources with Transifex
# http://transifex.com
#
# Note that this script updates or creates entries in .tx/config file
#
# Tim Sutton, March 2013

for ITEM in user-docs developer-docs tutorial-docs
do
  for POFILE in `find docs/i18n/en/LC_MESSAGES/${ITEM}/ -type f -name '*.po'`
  do
    # get the po file replacing 'en' with '<lang>'
    GENERICFILE=`echo $POFILE | sed 's/\/en\//\/<lang>\//g'`
    echo $GENERICFILE
    # Get the filename only part of the po file so we can use that
    # name when registering the resource
    BASE=`basename $GENERICFILE .po`
    BASE=`echo $BASE | sed 's/_/-/g' | sed 's/ /-/g'`
    # Register each po file as a transifex resource (an individual translatable file)
    tx set -t PO --auto-local -r inasafe.${ITEM}-$BASE \
      "$GENERICFILE" \
      --source-lang en \
      --execute
  done
done

#Print out a listing of all registered resources
tx status

# Push all the resources to the tx server
tx push -s