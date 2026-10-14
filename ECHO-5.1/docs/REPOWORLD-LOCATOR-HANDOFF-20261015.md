# ECHO-5.1 — traspaso explícito locator→editor, detección de lecturas redundantes y reserva de presupuesto

Fuente de implementación: rama `research/echo-5.1-pcworld1`.
Estado: corrección implementada y verificada localmente con pruebas unitarias y smoke en Bubblewrap.
0 GPU y 0 llamadas LLM consumidas en esta entrega. El contrato permanece en `design`, sin lanzamiento.

## Diagnóstico abordado (Calibración V2)

La calibración remota V2 sobre `sympy__sympy-19007` (2× Tesla T4, Qwen2.5-Coder-32B) confirmó que:
- La navegación por AST (`file_outline`) y las líneas atómicas sin mutilaciones funcionaron correctamente.
- El modelo observó `BlockMatrix._entry` (líneas 235–247) y mantuvo el método completo en su contexto.
- Sin embargo, el modelo repitió lecturas idénticas de las mismas líneas y, al alcanzar el límite de localización, emitió 7 llamadas adicionales a `file_view` rechazadas consecutivamente por cuota.
- El localizador consumió 24.155 tokens de los 25.000 asignados al episodio. Cuando finalmente emitió `finish`, el traspaso al editor se ejecutó con solo 845 tokens restantes, provocando `ContextOverflow` / `budget_stopped` antes de poder proponer un parche.

## Cambios implementados

### 1. Traspaso explícito locator→editor y guía en el contexto

- **`ROLE_POLICY_V2`**: Define directrices inequívocas para el rol `locator`:
  > *"Locate likely production functions with bounded search/reading. When target source lines appear in source_evidence, call finish immediately to hand off to editor. Do not repeat identical reads or attempt patch_apply as locator."*
- **`POLICY_V2`**: Aclara que el localizador dispone de hasta 8 llamadas y debe emitir `finish` en cuanto las líneas objetivo figuren en `source_evidence`.
- **Guía contextual activa**: En cuanto `source_evidence` fija líneas observadas del archivo, `context['feedback']` inyecta `handoff_ready: True` y `guidance: 'Target lines pinned in source_evidence. Call finish to hand off to editor.'`, eliminando la ambigüedad sobre la acción requerida.

### 2. Detección de lecturas redundantes y ruptura del bucle

- **`repoworld/source_evidence.py`**: `record_view()` compara las líneas devueltas con las ya autenticadas en `observed_lines()`. Si todas las líneas solicitadas ya estaban presentes para el contenido actual del archivo, se etiqueta `reply['redundant'] = True`.
- **Feedback accionable**: Ante una lectura redundante, el supervisor devuelve:
  > *"Redundant view: all requested lines are already recorded in source_evidence. Call finish to hand off to editor and propose your edit, or finish to terminate if unobserved."*
- **Ruptura mecánica tras reincidencia**: Si el modelo realiza 2 lecturas redundantes consecutivas (`redundant_reads >= 2`) y cuenta con un locus observado (`projection(session) is not None`), el supervisor ejecuta el traspaso automático a `role = 'editor'`, desbloqueando la fase de edición.

### 3. Reserva estricta de presupuesto y abandono sin alucinación

- **Techo del localizador**: El rol `locator` tiene un sub-presupuesto de 8.000 tokens.
- **Garantía para el editor**: Se reservan $\ge 17.000$ tokens (del total de 25.000 del episodio) exclusivamente para la fase de edición, crítica, ejecución de pruebas y reparaciones.
- **Traspaso por cuota / presupuesto**:
  - Si el localizador alcanza 8 llamadas (`localization >= 8`), 2 lecturas redundantes o 8.000 tokens:
    - **Con locus observado** (`projection is not None`): traspaso automático a `role = 'editor'`.
    - **Sin locus observado** (`projection is None`): el supervisor declara abandono limpio (`status = 'finished'`, parche vacío, `task_success = False`), registrando la decisión en los recibos sin forzar al editor a inventar código de la nada.

## Verificación offline (0 GPU)

1. **`tests/test_repoworld_interface_v2.py`**:
   - 16 pruebas pasadas (4 pruebas nuevas añadidas):
     - `test_v2_locator_repeated_reads_warn_and_hand_off_to_editor`: confirma aviso ante lectura redundante y traspaso automático tras 2 redundancias.
     - `test_v2_locator_quota_with_locus_hands_off_to_editor`: confirma traspaso al editor al agotar 8 llamadas con locus fijado.
     - `test_v2_locator_quota_without_locus_abandons`: confirma terminación limpia sin forzar edición cuando no se descubrió código.
     - `test_v2_locator_token_budget_cap_reserves_editor_tokens`: confirma traspaso por techo de tokens ($\ge 8.000$) y reserva de $>10.000$ tokens para el editor.
2. **Suite completa de RepoWorld**: **175 pruebas pasadas, 3 opcionales omitidas**, 0 fallos.
3. **Suite completa de PCWorld**: **257 pruebas pasadas**, 0 fallos.
4. **Suite de diseño**: **13 pruebas pasadas**, 0 fallos.
5. **Total general de pruebas**: **445 pruebas pasadas, 3 omitidas, 0 fallos**.
6. **Smoke hermético en Bubblewrap**:
   - `sympy__sympy-19007`: `valid: true`, `replay_identical: true`, `rollback_observed: true`, `source_unchanged: true`, 0 reservas pendientes.

## Próximos pasos

1. Renovar las compuertas locales (`software`, `smoke`, enlace de `official-controls` y `preflight`) bajo el nuevo manifiesto de fuentes.
2. Comprobar la frontera del proveedor con `operate.py check` offline.
3. Iniciar el entorno en Kaggle (2× T4) y ejecutar la calibración v4 reservada sobre `sympy__sympy-19007` para observar la generación real de un parche por el modelo 32B.
