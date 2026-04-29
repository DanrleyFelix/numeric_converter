PYTHON ?= python
SUPPORTED_OSES := windows linux macos

ifeq ($(origin OS), command line)
BUILD_OS := $(strip $(OS))
else
BUILD_OS :=
endif

.PHONY: preview run test build

preview:
	$(PYTHON) main.py

run: preview

test:
	$(PYTHON) -m pytest

build:
ifeq ($(BUILD_OS),)
	$(error OS is required. Use: make build OS=windows|linux|macos)
endif
ifneq ($(filter $(BUILD_OS),$(SUPPORTED_OSES)),$(BUILD_OS))
	$(error Unsupported OS '$(BUILD_OS)'. Use: windows, linux, or macos)
endif
	$(PYTHON) build/build_app.py --os $(BUILD_OS)

