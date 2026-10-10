.PHONY: help setup check test inventory

help:
	@echo 'make setup : crear .venv propia con Python 3.12.13'
	@echo 'make check : comprobar entorno y sintaxis'
	@echo 'make test  : ejecutar unittest; codigo 2 si aun no existen pruebas'
	@echo 'make inventory : regenerar catalogo estatico del codigo previo'

setup:
	python3.12 -I scripts/dev.py setup

check:
	.venv/bin/python -I scripts/dev.py check

test:
	.venv/bin/python -I scripts/dev.py test

inventory:
	.venv/bin/python -I scripts/inventory.py
