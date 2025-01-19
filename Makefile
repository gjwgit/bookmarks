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
