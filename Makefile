PROJECT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
SHELL := /usr/bin/env bash
.PHONY: inspect setup profile-check dev dev-desktop build validate test clean
inspect:
	$(PROJECT)/scripts/inspect-host.sh
setup:
	$(PROJECT)/scripts/install-dependencies.sh
profile-check:
	$(PROJECT)/scripts/validate-profile.sh
dev:
	$(PROJECT)/scripts/dev-session.sh --app
dev-desktop:
	$(PROJECT)/scripts/dev-session.sh --desktop
build:
	$(PROJECT)/scripts/validate-profile.sh
	$(PROJECT)/scripts/build-iso.sh
validate:
	$(PROJECT)/scripts/verify-iso.sh
test:
	$(PROJECT)/scripts/test-boot.sh
clean:
	$(PROJECT)/clean.sh
