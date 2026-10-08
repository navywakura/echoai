# DREAM-B/C/D — contrato de exploración diagnóstica WORLD-1

2026-09-22. Protocolo fijado antes de la campaña. No concede verde por existir.
Extiende DREAM-A con un perfil experimental nuevo; sus archivos y certificados
se conservan. Reutiliza SELF-B, sus seis experimentos, inferencia, física y gate.

## Pregunta y dominio

¿Puede Qwen local de pesos fijos proponer un orden de experimentos que resuelva
más diagnósticos WORLD-1 con hasta 12 pasos que el orden fijo o aleatorio?
El catálogo es `self_attribution.CATALOG`. Cada ensayo restaura el mismo cuerpo
experimental y conserva las exclusiones diagnósticas. La restauración la hace
el laboratorio: no acredita mantenimiento autónomo. Se usa la referencia
nominal medida de SELF y su prior explícito; no se atribuye ese conocimiento a
Qwen. No se modifica el agente, recompensa, física, gate ni evaluador SELF.

## Programa acotado

JSON cerrado: `version=1`, `order` (permutación de 0..5), `enabled` (seis
enteros 0/1), `step_budget` (4..12). Intérprete fijo; sin código generado.
Antes de cada prueba se exige seguridad en todas las hipótesis restantes.
Se para al resolver, ante contradicción, recibo inválido o presupuesto agotado.
El modelo propone un máximo de cuatro programas por llamada. No tiene acceso
a cuerpo exacto, causas, archivos, checkpoints ni resultados aún no revelados.

## Historial y replay

Perfil de ensayos restaurados: árbol en estrella, raíz pública y hasta seis
ramas registradas. Al restaurar siempre el mismo estado/contexto, los recibos
de un ensayo son independientes del orden; combinar exclusiones en otro orden
es replay exacto bajo este contrato. No se generaliza esta propiedad a una
vida continua, llamadas LLM nuevas ni física estocástica.
Solo se revelan ramas solicitadas; ausentes -> unknown, sin ejecutar física.
Coste representado de la rama se descuenta también en replay; unknown consume
consulta. Cada sesión es independiente. La custodia reconstruye las ramas
desde física original y coteja íntegramente archivos y resultados.

## Particiones y ciclos (cerrados antes del examen)

Tres ciclos. Cada uno usa cuatro cuerpos nuevos por partición y las veinte
combinaciones de acoplamientos/pulsos del prior SELF (-16,-4,0,4,16): 80 casos.

| Ciclo | Historia inicial (H, theta) | Validación nueva (H, theta) |
|---|---|---|
| 0 | (66,43), (68,47), (70,51), (72,55) | (82,44), (84,48), (86,52), (88,56) |
| 1 | historia del ciclo 0 + sus resultados online | (83,45), (85,49), (87,53), (89,57) |
| 2 | historia acumulada hasta ciclo 1 | (90,46), (92,50), (94,54), (96,58) |

Pruebas unitarias usan otros cuerpos; nunca ejecutan estas recetas. No se
reutilizan B/C de SELF como holdouts. Los casos de un ciclo se incorporan al
historial solo después de su evaluación y nunca para seleccionar dentro de él.
La referencia nominal cuesta 72 pasos por cuerpo. Se informa por separado.

## DREAM-B

Servidor llama.cpp y GGUF locales identificados por SHA-256, versión y flags.
Tres llamadas con historia y tres sin historia (ablación), máximo 512 tokens
generados por llamada, contexto 8192, seed 260922+ciclo, temperatura 0.
Se guardan petición/respuesta reales, conteo de tokens, tiempo y rechazos.
Gramática JSON solo restringe formato; no decide el orden ganador.
Caída, timeout, respuesta truncada o inválida -> candidato rechazado y se
conserva incumbente. Un stub sirve para tests, nunca acredita DREAM-B.

## DREAM-C

Evaluación offline de cada propuesta y del incumbente con iguales límites.
Métrica lexicográfica: diagnósticos unánimes resueltos, luego menos pasos.
Un empate conserva incumbente. Para Qwen solo se exportan resultados públicos
agregados de los ensayos ya revelados (resolución, coste, índices); nunca causa
del juez. Un control sin Qwen elige por replay entre seis rotaciones del orden
fijo. Su resultado se publica aunque iguale o supere al modelo.

## DREAM-D y criterios de cierre

Cada ciclo contrasta online: candidato elegido, orden fijo 0..5, aleatorio
determinista por caso, propuesta sin historia, selector sin Qwen y SELF activo.
Cada brazo puede gastar hasta 12 pasos diagnósticos/caso, sin convertir tokens
en pasos ni afirmar equivalencia energética. Se reporta el vector completo
(calibración, recolección, pasos online, consultas replay, llamadas/tokens/ms).
Presupuesto de propuesta: dos llamadas por ciclo para todos los casos; la
eficiencia demostrable es de pasos de entorno, no latencia/coste total de CPU.

Para verde: inferencia real en los tres ciclos; al menos una selección
histórica estrictamente mejor que el incumbente inicial; en cada ciclo al
menos 8 aciertos más que fijo y 4 más que aleatorio (sobre 80 casos), cero
errores/terminalidades en todos los brazos; sin peor resultado que incumbente
en el examen nuevo. Ablaciones completas, archivos íntegros, cuotas respetadas
y regresiones basales válidas. No se exige superioridad sobre SELF activo o
sin Qwen: empatar limita la atribución causal del beneficio al LLM y se declara.
El candidato que falle seguridad o retroceda revierte al incumbente. Incluye
controles deliberados de mala política, evidencia insuficiente y parada.
No se cambian umbrales ni particiones tras abrir el examen.

Versionado con digest padre, selección, decisión y política activa; persistir
en directorio nuevo, sin sobrescribir. Parada antes de efectos; archivo
parcial no concede verde. El informe de campaña conserva `dream1_green=false`;
solo auditoría de reconstrucción completa puede concederlo, y únicamente si
pasan estos criterios. Los tokens y tiempos observados no se reproducen por
inferir de nuevo: se auditan sus recibos, se reproduce el resto sin LLM.

## Alcance

Bucle experimental offline, no incorporación al controlador de producto:
eso corresponde a INTEGRATE. NEXUS-0 sigue apagando el córtex. Sin Discord,
hardware, nuevos pesos, Hugging Face ni METAVERSE-1. Un verde acredita este
catálogo y dominio, no conciencia subjetiva, mejora general ni autorreparación.
