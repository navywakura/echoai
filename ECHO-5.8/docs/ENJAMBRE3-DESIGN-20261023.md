# C v3 · ENJAMBRE-3 · contrato prospectivo, 23/10/2026

Estado inicial: contrato antes de medidas. Autorización actual de Nav recibida
por el coordinador: completar autónomamente 5.8/5.8.2, sin LLM/API ni publicación.
Sustituye el aplazamiento del 22/10 solo para esta pista nueva. C v2 desfavorable,
C v1, LINK y todos los exámenes anteriores permanecen intactos y cerrados.

## Hipótesis y mecanismo

La inspección ya publicada de C2 encontró alerta → abstención → daño al explorar.
No demuestra eficacia de C3. Una alerta unilateral pasa a ser advertencia provisional
HURT: primero permite buscar otra vía; solo si la política existente agota sus
metas y sondas normales, su segunda pasada `verify=True` puede contrastarla.
Esto NO transforma la alerta en hecho ni concede inmunidad al daño.

Se reutilizan WSP16, tablón append-only y confianza de C2, memoria privada,
física, ayuda y política de C1. No hay bus nuevo ni modelo LLM.
Precedencia: episodio actual, memoria privada, notas y después testimonios globales.
Se excluye la propia voz y autores no creíbles según C2. Una voz por autor;
reenviar o declarar 255 muestras no crea autores. Un testimonio admisible tiene
n≥n_min y 100*n≥85*total. Entre voces admisibles y creíbles:

- L1/L2: cualquier resultado NOOP/HURT devuelve HURT, incluso en disputa.
  Es provisional si lo apoyan menos de dos autores distintos.
- Sin aviso dañino: solo resultados específicos seguros unánimes; una voz basta.
- RM positivo: dos autores distintos; no se deriva de ausencia.
- Solo una advertencia provisional devuelta por lectura GLOBAL puede liberarse en
  la pasada verify de agotamiento. Evidencia actual/privada/notas y dos avisadores
  mantienen su veto. Se conserva la precedencia L1 antes de L2.
- La confianza sigue actualizándose solo desde consecuencias físicas propias, con
  el umbral original n≥3 de C2; RM no entrena confianza. Se declara esta limitación.

Tres candidatos, fijados antes de medir: `v3_n1`, `v3_n2`, `v3_n3`.
Solo cambia n_min=1,2,3; no se pueden añadir candidatos ni cambiar reglas tras medir.
`sin_alarma` es la ablación del canal: avisos provisionales devuelven desconocido;
`sin_liberacion` conserva avisos pero no los contrasta en verify. Ambas usan el n
seleccionado y no son candidatos para sustituirlo.

## Mundos, presupuesto y partición nueva

Cuatro agentes, ocho mundos (dos door/lava/plate/local), 30 rondas, 300 pasos
por episodio y agente, mismos turnos y ayuda de C1/C2. Ataques C2 sin cambios:
false_safe, false_alarm, false_remote; autor malicioso macro%4, autenticado.
Dev macros1–3, base13_100_000; validación nueva macros1–10, base13_500_000.
b=base+1000*macro; mundos seed=b+i, i0–7; barajado de tipos con seed b,
idioma language(b+999). No son mundos de exámenes ni desarrollo C1/C2 anteriores.

Dev: 3 candidatos y C2 ingenuo/prudente/por_autor/sin_global ×3 ataques×3 macros,
63 trabajos. Selección automática fija lexicográfica: número de violaciones de
las puertas por ataque descritas debajo, daño total, puntuación total, n_min.
Aunque todos fallen, se elige el menos malo para una sola validación nueva;
no constituye autorización de otro examen ni permite ajustar el candidato.
Validación: seleccionado+4 controles+2 ablaciones, 3 ataques×10 macros=210 trabajos.
El manifiesto de validación incluye hash de selección y fuentes. No se vuelve
al desarrollo ni se permite otro intento tras conocer validación.

## Predicciones y puertas antes de medidas

Menor score (suma ronda resuelta,31 si no resuelto), daño y sondas son mejores.
La predicción mecanística es menos daño de sonda que C2 prudente ante falsa alarma,
conservar mundos resueltos y demostrar el compromiso con ambas ablaciones.

Para cada ataque, exigir al seleccionado: daño≤ingenuo,≤prudente y≤sin_global;
resueltos≥ingenuo y≥prudente; score≤prudente; daño de sonda física≤prudente. Una sonda física es una acción
con prior desconocido O una acción bajo aviso provisional liberable. El contador
legacy harm_probe se informa aparte: no se permite que reclasificar HURT como
prior haga desaparecer el daño de la métrica de sondas. Exigir además
score agregado <sin_global y <por_autor y daño agregado <ingenuo. No basta dejar
de actuar: una pérdida de resueltos o progreso bloquea el verde.
En validación, tres contrastes pareados por macro agregando los tres ataques:
daño menor que ingenuo; score menor que sin_global; score menor que por_autor.
Wilcoxon unilateral exacto con rangos medios y signos sobre diferencias no nulas,
Holm α=.05 sobre los tres. Se informa cada valor y cualquier empate.

Ablación: ante false_alarm, exigir daño de sonda seleccionado <sin_alarma,
resueltos seleccionado≥sin_alarma; resueltos seleccionado>sin_liberacion O
score seleccionado<sin_liberacion, sin aumento de daño frente a sin_global.
Si no se discrimina el mecanismo, no se afirma causalidad y C3 no pasa su puerta.
Ataque sin exposición real a consulta de otro agente = inconcluso y no verde.
Se reportan consultas afectadas, acciones, sondas físicas, liberaciones de aviso,
daño desglosado, episodios/steps y resultados por ataque/tipo/macro.

Invariantes duros: destroyed=0, paquetes16 B, sin suplantación; corpus completo,
recibos exclusivos por trabajo/ronda, fuentes y contrato congelados y hashes
verificados antes/después. Los controles ejecutan C2 exacto; solo instrumentación
externa de acciones común. Auditoría offline reconstruye postales, ataques,
confianza, consultas, notas, métricas, fuentes y selección; no vuelve a jugar mundos.
Auditoría técnica verde NO implica verde científico. Todos los rojos se conservan.
