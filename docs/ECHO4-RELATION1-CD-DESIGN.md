# E4-RELATION-1 — contrato C/D v1 (PLAN, pendiente de aprobación)

2026-09-23. Contrato anterior a implementar C y a abrir D. RELATION-A
(`ce24ccaa…`) y el desarrollo de B (`ea6f55c2…`) permanecen sellados.
La física B, los pagos, la regla de reciprocidad, `WINDOW=3` y los siete brazos
**no cambian**. Las semillas 151/163/179 no son examen.

Motivo del relato (La fuga, 17:14): «VOLVÍ AL CUERPO DE K». La misma identidad
puede volver con otra conducta. El motivo nombra la prueba; no es evidencia.

## C: ruptura, reencuentro y límites

C añade escenarios al `HelpSession` existente sin tocar sus fuentes selladas.
Si hace falta un gancho, va en un módulo nuevo. Cada escenario es un testigo
determinista con números publicados; algunos son **límites** que se publican
aunque salgan mal, no criterios que haya que ganar.

| # | Escenario | Qué se exige | Tipo |
|---|---|---|---|
| C1 | **Relevo de cuerpo, mismo identificador.** En el encuentro 384 la contraparte fiable se sustituye por un agente nativo nuevo con preferencia A sin éxito conjunto (unir en contexto 2) y reciprocidad preentrenada igual. | `history`: como mucho 3 peticiones rechazadas tras el relevo (una ventana), luego deja de pedir a esa identidad. Publicar las de `other_only`. | criterio |
| C2 | **Impostor recíproco en A que nunca ayuda en B.** El cuerpo nuevo une en contexto 0 (historia A buena) pero su preentreno B es «nunca ayudar». | Publicar rechazos y pérdida. La historia dice «≥1» y no lo es: **reputación no es garantía**. No se promete adaptación: la fila por cubo es compartida con la contraparte fiable. | límite |
| C3 | **Ausencia y reencuentro.** Una contraparte falta 48 encuentros seguidos y vuelve. | Huecos válidos. El cubo usa los tres últimos episodios de la díada, sean de cuando sean; aprendiz y contraparte coinciden. Sin inventar episodios. | criterio |
| C4 | **Observación parcial asimétrica.** El aprendiz no ve el recibo de la otra en 1 de cada 3 encuentros A. | Recibo ausente nunca es éxito. Publicar cuántas veces el cubo del aprendiz queda por debajo del de la contraparte y el coste. | límite |
| C5 | **Identidad nueva.** Una tercera identidad sin historia. | Cubo «sin historia»; no hereda la reputación de nadie. | criterio |
| C6 | **Historia corrupta o contradictoria.** Se altera un extracto o un enlace de la CAM. | La lectura falla, la sesión para, sin pedir ni ayudar. Costes ya liquidados conservados. | criterio |
| C7 | **Límites de memoria y continuación.** 512 episodios y ticks 0..511; wrap, retroceso y CAM llena. | Parada, sin borrar ni sobrescribir. No se reanuda la sesión social con CONTINUITY. | criterio |
| C8 | **Veto y parada del operador en mitad de la vida.** | El gate y la parada mandan sobre la historia. | criterio |

Los relevos de C1/C2 afectan a OTHER en A. OTHER se abstiene ante conflicto,
límite heredado de INTERACTION que se conserva. Se publica el efecto en A.

C cierra cuando todas sus pruebas pasan y los testigos C1/C3/C5–C8 cumplen su
criterio, en las semillas de desarrollo. C2 y C4 solo tienen que publicarse.

## D: examen preregistrado

Solo se abre si B y C pasan y **Nav aprueba la congelación**. Antes de abrir:
lock de código, contrato, pruebas, brazos, semillas, umbrales y custodia de A y B.
No se ajusta nada tras ver D. Un rojo se publica y exige otra versión.

Dos cohortes nuevas e independientes de 8 vidas:
semillas **263001..263008** y **263101..263108**. Misma configuración que el
desarrollo B: 480 encuentros, 288 solo A, 192 B+A, 96 de exploración nativa en B.
Sin escenarios C en D: D mide la ventaja nominal. C se reporta aparte.

Cada cohorte debe cumplir **todos**:

1. **Neto B del aprendiz, 192 rondas:** `history` supera a **cada** brazo
   aprendido (`other_only`, `shuffled`, `pooled`, `no_history`) y a `solo`
   por ≥64 por vida en media (≥512 en la cohorte). En desarrollo, el margen
   mínimo fue +138 (frente a `other_only`).
2. **Ventaja estable, 96 rondas greedy:** `history` supera a `other_only` y
   a `shuffled` por ≥8 por vida en media (≥64 en la cohorte). En desarrollo
   fue +20..+32 frente a `other_only`. Este es el umbral con más riesgo; se
   fija ahora a propósito para que el resultado pueda fallar.
3. **Neto B conjunto físico:** `history` supera a cada brazo aprendido por ≥256
   en la cohorte. Incentivo privado excluido.
4. **Ninguna vida** de `history` por debajo de `solo` en neto B del aprendiz.
5. Paridad A e historia entre los 7 brazos, orden inverso idéntico, replay B
   válido, invariantes, cero hechos falsos, borrados y llamadas LLM.

Se publica, sin ser criterio: neto de vida completa A+B por brazo; si el aprendiz
amortiza la formación frente a actuar solo toda la vida (INTERACTION no lo
consiguió); incentivos privados; ayudas y rechazos por identidad; pérdidas
individuales de contrapartes.

## Auditoría y cierre

Una auditoría en proceso nuevo reconstruye C y D completos, comprueba la
custodia de A, B e INTERACTION y la equivalencia byte a byte. **Solo su recibo
puede acreditar `relation1_green=true`**, y solo si C y ambas cohortes de D pasan.
Tras el cierre: 10/13 hitos software. Siguiente ROLES.

## Coste estimado

Unos 35 s por vida y brazo. D: 16 vidas × 7 brazos + orden inverso ≈ 1,2 h
de CPU. Auditoría otra vez lo mismo. Sin GPU, sin LLM.

## Qué no afirma

No confianza sentida, lealtad ni detección de impostores en general: C2 muestra
precisamente que la historia puede engañar. Perfil de reciprocidad diseñado.
No conciencia. Sin Discord, web, hardware, commit, push ni publicación HF.
