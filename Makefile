PROJECT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
PYTHON ?= python3
SHELL := /usr/bin/env bash
.PHONY: inspect environment application-audit setup profile-check native native-check desktop-check gtk-check dev dev-desktop build build-hyprland validate test test-live-account test-uefi clean
inspect:
	$(PROJECT)/scripts/inspect-host.sh
environment:
	python3 "$(PROJECT)/scripts/build-environment.py"
application-audit:
	python3 "$(PROJECT)/scripts/application-audit.py"
setup:
	$(PROJECT)/scripts/install-dependencies.sh
profile-check:
	$(PROJECT)/scripts/validate-profile.sh
native:
	bash "$(PROJECT)/scripts/build-native.sh"
native-check:
	bash "$(PROJECT)/scripts/check-native.sh"
desktop-check:
	python3 -m unittest discover -s "$(PROJECT)/tests" -p 'test_*.py'
gtk-check:
	FETIAN_GTK_TEST=1 GDK_BACKEND=x11 GSK_RENDERER=cairo GTK_A11Y=none dbus-run-session -- xvfb-run -a $(PYTHON) "$(PROJECT)/tests/gtk_files_smoke.py"
dev:
	$(PROJECT)/scripts/dev-session.sh --app
dev-desktop:
	$(PROJECT)/scripts/dev-session.sh --desktop
build:
	$(PROJECT)/scripts/validate-profile.sh
	$(PROJECT)/scripts/build-iso.sh
build-hyprland:
	$(PROJECT)/scripts/validate-profile.sh
	FETIAN_DESKTOP=hyprland "$(PROJECT)/scripts/build-iso.sh"
validate:
	$(PROJECT)/scripts/verify-iso.sh
test:
	$(PROJECT)/scripts/test-boot.sh
test-live-account:
	FETIAN_EXPECT_LIVE_ACCOUNT=1 "$(PROJECT)/scripts/test-boot.sh"
test-uefi:
	python3 "$(PROJECT)/scripts/vm-test.py" --expect live-account
clean:
	$(PROJECT)/clean.sh
