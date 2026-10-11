.PHONY: help setup check test inventory bench audit setup-sandbox panel checks-background development-background confirmation-background
OUT ?= artifacts/integration-20261010

help:
	@echo 'make setup : crear .venv propia con Python 3.12.13'
	@echo 'make check : comprobar entorno y sintaxis'
	@echo 'make test  : ejecutar pruebas unitarias e integracion CPU'
	@echo 'make inventory : regenerar catalogo estatico del codigo previo'
	@echo 'make bench OUT=artifacts/nombre-nuevo : banco sintetico controlado'
	@echo 'make audit OUT=artifacts/nombre : recalculo y replay independiente'

setup:
	python3.12 -I scripts/dev.py setup

check:
	.venv/bin/python -I scripts/dev.py check

test:
	.venv/bin/python -I scripts/dev.py test

inventory:
	.venv/bin/python -I scripts/inventory.py

bench:
	.venv/bin/python -I scripts/run.py bench --output "$(OUT)"

audit:
	.venv/bin/python -I scripts/run.py audit "$(OUT)" --replay

setup-sandbox:
	python3.12 -I scripts/setup_sandbox.py

panel:
	.venv/bin/python -I scripts/background.py panel

checks-background:
	.venv/bin/python -I scripts/background.py checks

development-background:
	.venv/bin/python -I scripts/background.py development --workers 4

confirmation-background:
	.venv/bin/python -I scripts/background.py confirmation --workers 4
