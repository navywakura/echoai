# E4-RELATION-1 — RELATION-C implementada, testigos de desarrollo válidos

2026-09-23. [Contrato C/D](ECHO4-RELATION1-CD-DESIGN.md), aprobado.
Auditoría en proceso nuevo válida, cero hallazgos. Digest
`ac7a1aab95f228270142d6dc49d05edf96287e5485b9cc06c0e3c3c9253df3cb`.
`relation1_green=false`: D sigue sin abrir. Custodia de A (`ce24ccaa…`) y
del desarrollo B (`ea6f55c2…`) comprobada en la propia campaña.

[Informe](../lab/echo4/relation1-c-dev-v1/report.json) ·
[Testigos](../lab/echo4/relation1-c-dev-v1/witnesses.json) ·
[Código](../echo4/relation_c.py) · [Banco](../echo4/relation_c_bench.py) ·
[Pruebas](../tests/test_echo4_relation1c.py).

Las fuentes selladas de B no se tocan. `RelationCSession` añade el relevo de
cuerpo y la parada ante fallo. En sesiones nominales reproduce exactamente
el desarrollo B sellado (testigo C0).

## Testigos, semillas 151 / 163 / 179

| # | Escenario | Resultado | Tipo |
|---|---|---|---|
| C1 | Relevo del cuerpo fiable en el encuentro 384; mismo identificador, sin memoria del aprendiz | `history`: 3/1/3 peticiones rechazadas y deja de pedir. `other_only`: 9/10/12. Neto B 348/356/360 frente a 178/194/206 | criterio ≤3, **cumple** |
| C2 | Impostor: une bien en A, nunca ayuda en B | 4/4/4 rechazos. Neto B 344/344/356 frente a 606/600/630 nominal. Tras los rechazos, la fila «≥1 éxito» se vuelve negativa y el agente deja de pedir **a cualquiera**. La historia buena engañó 4 veces | límite publicado |
| C3 | Una contraparte ausente 48 encuentros y reencuentro | Cubos de aprendiz y contraparte coinciden en todos los pasos; episodios por díada = encuentros reales | criterio, **cumple** |
| C4 | El aprendiz no ve el recibo ajeno 1 de cada 3 encuentros A | Cubo del aprendiz por debajo del de la contraparte 27/28/20 veces, nunca por encima. Neto B 454/442/510 frente a 606/600/630 | límite publicado |
| C5 | Identidad nueva que aparece por primera vez en B | `history`: cubo «sin historia» en 3/3. `pooled` hereda la reputación ajena (2/1/2) | criterio, **cumple** |
| C6 | Extracto de episodio alterado | La lectura falla, la sesión para, sin pedir ni ayudar; libros y turnos intactos | criterio, **cumple** |
| C7 | 512 episodios y CAM llena | 512 episodios, cierre limpio tras el límite; CAM llena para la sesión; cero borrados | criterio, **cumple** |
| C8 | Veto del operador en el encuentro 400 (`always_ask`) y parada | 80 pasos vetados, 0 peticiones; tras parar, no continúa | criterio, **cumple** |

8 pruebas nuevas de C. El invariante explícito de C coincide con el heredado
en sesiones nominales y registra los encuentros del cuerpo retirado sin
reatribuirlos al nuevo.

## Lectura

La historia reciente protege frente a un cambio de cuerpo **si ese cambio se ve
en A** (C1): una ventana de 3 episodios basta. No protege si el nuevo cuerpo
imita la conducta A pero no la B (C2), y además contamina la decisión con la
contraparte que sí era fiable, porque la fila por cubo es compartida. Esto
es un límite del diseño de B, no un fallo que haya que ocultar.
«Reputación no es garantía».

Hubo ejecuciones exploratorias de C durante la implementación, antes de fijar
las fuentes. Una de ellas encontró que el invariante heredado no admitía el
relevo, y se corrigió antes de sellar.

## Siguiente: D

Módulo `echo4/relation_d.py` preparado: lock, criterios del contrato y
auditoría. La pasada en seco con semillas de desarrollo, que no es evidencia,
cumple los cinco criterios. **D solo se abre con la Aprobado: para congelar.**
