# Encargo propuesto para B21

Documento para revisión y futura implementación. No implementado ni lanzado
el 6 de octubre de 2026. El encargo actual solo reúne documentos y logs.

Trabaja en `/home/roger/REALRXOS/RXos/echoai`. Lee las instrucciones del repo,
`CLAUDE.md`, `docs/05-NEXUS-0-SPEC.md`, el expediente B20, su contrato y
`docs/ECHO45-S6-B21-PROPOSAL.md`. Respeta privacidad, fuentes congeladas,
córtex apagado en NEXUS-0, bus existente y separación de proyecto legacy.

Antes de cambiar código, espera el cierre B20 y verifica artefactos finales:
micro, auditoría, revisión aritmética, presupuesto y hashes. Exporta los 144
pasos y tres respuestas iniciales. Distingue propuestas únicas, firmas de
conducta y recorridos duplicados. No atribuyas a un fallo de formato los 144
veredictos V3 ni atribuyas causalidad a un ranking sin medir el contraste.

Investiga por qué la exploración sin padre solo ofrece HOLD=0, cuándo pasa a
otro valor, qué guardas se ven pero no se seleccionan y si los descendientes
heredan una condición que excluye una reparación. Mantén la solución del
control humano solo en el análisis del auditor, fuera del paquete del agente.

Primero formaliza B21-A: mismo actor/lenguaje/juez y comparación de B20,
exploración balanceada y muestreo de gramática. Fija propuestas, semillas,
partidas, coste total, trazabilidad de cobertura y regla de selección antes de
medir. Usa fuentes nuevas; no edites módulos B18/B19/B20 ni sus dependencias
congeladas. Identifica resultados de desarrollo retrospectivo y reserva
confirmatoria sin exposición previa. No aumentes intentos por un rechazo.

Si B21-A no resuelve el cuello, prueba las hipótesis temporales por etapas:
EPISODE-1, CREDIT-1, REPLAY-1 y CONSOLIDATE-1. Usa observaciones propias, memoria
acotada e incertidumbre explícita. Mantén enteros en el núcleo rápido y reutiliza
memoria/bus existentes. Un estado privado del simulador no es una feature del
agente. Una huella de elegibilidad no es evidencia causal ni implementación
biológica certificada.

Antes de interpretar un contrafactual, reproduce exactamente el snapshot
basal completo con agente, entorno, memoria y RNG. Si no puedes garantizarlo,
repite el episodio desde su inicio. Nunca puntúes una política nueva leyendo
solamente la trayectoria de la anterior.

Compara memoria activa/apagada y neocórtex inicial/en bucle con ablaciones y
coste completo. Mantén el modelo cualificado inicialmente. Tres generaciones
en lugar de una constituyen una intervención y se contabilizan, incluidos
fallos y reintentos. No proclames igualdad de cómputo solo porque ambos brazos
tengan 18 candidatos. Calibra y congela presupuesto total común para el ensayo
de superioridad. La variante solo inicial conserva su definición.

Pruebas previas deben detectar: sesgo a duración cero, ramas duplicadas,
estado temporal que sobrevive indebidamente al reinicio, crédito que confunde
linajes o episodios, pérdida tardía no representada, candidato sin efecto,
certificado de otro perfil, restauración falsa, fuga de una regla humana,
feedback protegido y explicación inventada. Una prueba no debe exigir elegir
la guarda conocida; debe validar propiedades generales del investigador.

Conservar V3: +2 niveles y cero pérdidas individuales de niveles/score. Los +1
pueden orientar exploración pero no integrarse como mejoras aceptadas.
Composición de dos parches requiere una condición nueva y presupuesto común,
no una modificación silenciosa para salvar un resultado negativo.

Congela el primer ganador antes de desarrollo amplio y reserva. Audita con
caché independiente y métricas recalculadas por otro instrumento. No uses una
reserva fallida para refinar bajo el mismo nombre de examen. Solo después
habilita el contrato de piloto/campaña/examen desde SEMILLA, con los cuatro
brazos y B1-B5 intactos. Un pase B21 no declara por sí solo S6 verde.

Observabilidad: registrar solicitudes, propuestas exactas, shortlist, motivo
registrado de selección, padre, memoria consultada, hechos observados, coste,
predicciones, resultados y veredicto. Reutiliza el visor. El LLM puede traducir
telemetría; marca toda interpretación y ausencia de motivos. No inventes
pensamientos y no instrumentes reserva/examen.

No lanzar, gastar, publicar ni cambiar un modelo por este texto archivado.
La ejecución futura necesita un encargo activo y un contrato congelado.
Si se autoriza Kaggle privado, usar su GPU gratuita y el transporte de
credenciales existente sin imprimirlas ni incluirlas en artefactos.
