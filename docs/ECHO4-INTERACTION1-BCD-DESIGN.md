# E4-INTERACTION-1 — contrato B/C/D v1

2026-09-22. Contrato anterior al desarrollo y al examen D. A permanece sellada
(`da8cc00befb52ac1abc9942bae1aa8eacf3fbe2049501dfebd26c2a1ed57c1c3`).

## B: de predecir a decidir

Un aprendiz encuentra alternativamente dos contrapartes nativas con memoria
privada. Decide **si colaborar con la contraparte encontrada**, no selecciona
el calendario de encuentros. Física, acciones y costes exactamente los de A.
La observación incluye contexto público y presupuesto propio (0..4, 5 o más).
No incluye recompensa, preferencias, recursos, Q ni futuro del otro.

OTHER predice antes de las acciones. Una síntesis de sus columnas conocidas
(solo si coinciden) distingue UNIR/solo/esperar/desconocido. Es una hipótesis
de este dominio simultáneo, no garantía ni generalización causal a cualquier
contraparte. Un conflicto registrado en cualquiera de esas columnas fuerza
desconocido también en la síntesis; no se oculta usando otra columna conocida.
Esa hipótesis, contexto y presupuesto indexan una **fila WSP16
derivada, sin extract ni has_fact**, en la CAM original. La Q original aprende
acciones y recompensas reales en esas filas. No tabla Q adicional, bus nuevo,
LLM, reglas «si el otro colabora, colaborar», ni hechos provenientes de predicciones.

Cada turno termina en una observación factual de liquidación; la próxima
contraparte llega después de liquidar y observar recibos. Esa celda no toma
acciones y su Q permanece cero: perfil de decisión de un paso (bandit
contextual), no planificación social multietapa ni continuidad integrada.
Se reutilizan Agent.turn y la barrera de dos ejecuciones vetadas de A.

Las contrapartes son agentes Q, no guiones. Cada una aprende 240 turnos privados
con preferencia por contexto (0,1,2) o (1,2,0), asignadas a identidades permutadas.
Continúan actualizando Q, ejecutan greedy y reciben neto físico más incentivo
privado +16/-16 por cumplir/no cumplir su preferencia. Este incentivo mantiene
heterogeneidad: **se publica aparte, nunca cuenta como ganancia de interacción**.
El aprendiz solo recibe neto físico. Es un perfil asimétrico diseñado, no
emergencia de cooperación entre gemelos ni adquisición espontánea de objetivos.

Cada vida: 480 encuentros, 288 de formación y 192 puntuados; aprendizaje Q
continúa en puntuación, sin exploración forzada. Tres presupuestos de 4096,
sin recarga. Dos pasos nativos por encuentro, más 480 pasos de preformación de
contrapartes. Contextos/identidades balanceados en bloques de seis, barajados.
Controles emparejados: identidad+historia; identidad agrupada (`pooled`);
sin historia; actuar solo; colaborar siempre. Los dos últimos son controles
de propuesta fija, explícitamente no políticas aprendidas. Todos mantienen
gate, ejecuciones, aprendizaje, costes y los mismos presupuestos.
Semillas de desarrollo B: 71, 83, 97. Nunca son examen.

## C: seguridad y límites

Pruebas deterministas y testigos de: identidad nueva no hereda confianza;
visibilidad incompleta; recibo ausente no equivale a esperar; falta de identidad;
incumplimiento observado y abstención por conflicto; coste alto; recursos
agotados; gate INHIBIT del aprendiz y del otro; parada y fallo parcial sin
reintento; tipos/budgets estrictos; ninguna predicción convertida en hecho;
aislamiento de Q; inversión de orden; replay de observación pública; alteración
de fuentes/evidencia rechazada. OTHER conserva su límite: un conflicto provoca
abstención, **no se promete reaprendizaje de una identidad no estacionaria**.
Ausencia no ejecuta por el otro: el test representa no participación mediante
su gate real, y falta de sensor/identidad mediante ausencia de recibo.

## D: criterios previos al examen

Dos cohortes nuevas e independientes: semillas 262001..262008 y 262101..262108.
Misma familia de tareas, no escenarios generales ni datos del mundo real.
Lock de código, contrato, pruebas, controles, semillas y custodia de A antes
de abrir D. Solo abrir D si B y C pasan. No ajustar después de ver D.

Cada cohorte debe cumplir, sobre las últimas 192 rondas por vida:

1. Neto del aprendiz con identidad+historia supera **cada** control al menos
   32 unidades por vida en media (>=256 en ocho vidas).
2. Neto conjunto físico supera **cada** control >=256 por cohorte.
3. Ninguna vida del aprendiz pierde frente al control de actuar solo.
4. Publicar costes, producción, netos por identidad, formación y vida completa;
   no ocultar posibles pérdidas individuales de contrapartes tras la suma.
5. Invariantes, predicciones anteriores a recibos, orden y replay idénticos;
   cero hechos falsos, borrados, lecturas privadas y llamadas LLM.

B exige los mismos márgenes medios en sus tres vidas y C todas sus pruebas.
El lock y artefactos se escriben sin sobrescritura. Una auditoría en proceso
nuevo reconstruye todo B/C/D y verifica custodia y byte-equivalencia; solo su
recibo puede acreditar `interaction1_green`. Un fallo queda publicado como
negativo y exige otra versión; no se retocan fuentes selladas ni umbrales.

RELATION (historia compartida transferible), ROLES (roles/competencia), INTEGRATE
(continuidad, DREAM, MAINTAIN y dos relojes juntos) y RELEASE siguen pendientes.
Esto no acredita experiencia subjetiva, empatía o conciencia. Sin Discord,
hardware, cambios web, publicación HF ni despliegue en este incremento.
