########################################################################
#
# Makefile for updating and amanaging browser bookmarks.
#
# Time-stamp: <Monday 2025-01-20 08:52:23 +1100 Graham Williams>
#
# Copyright (c) Graham.Williams@togaware.com
#
# License: Creative Commons Attribution-ShareAlike 4.0 International.
#
########################################################################

# App is often the current directory name.
#
# App version numbers
#   Major release
#   Minor update
#   Trivial update or bug fix

APP=$(shell pwd | xargs basename)
VER=0.0.1
DATE=$(shell date +%Y-%m-%d)

########################################################################
# HELP
#
# Help for targets defined in this Makefile.

define HELP
$(APP):

  reset	     Upload bookmarks.json to firefox and brave.

endef
export HELP

help::
	@echo "$$HELP"

########################################################################
# LOCAL TARGETS

reset:
	python clear_firefox.py
	python upload_bookmarks.py
