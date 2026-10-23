# Archivos WSP · integración de episodios completos

Extensión de ingeniería posterior al benchmark de formato, que permanece
inmutable. Nav pidió que echoAI utilice los archivos. Además de las sondas
ya verificadas, ejecutar el Agent original con memoria cargada de `.wsp` en
mundos de desarrollo completos, sin modificarlo.

Crear `echo58/wspfiles/play.py`: CLI local carga archivo, crea mundo MiniGrid
mediante adaptador original y ejecuta `Agent(source=memory).run(world)`.
Un wrapper del mundo registra cada acción real y observación pública, sin
realimentar logs a la política. Nada de semillas o familias de examen.

Comprobación de integración fijada antes de ejecutar: tres familias de
entrenamiento (LavaGapS7, DoorKey6, DynObs6), dos semillas nuevas
202610230/202610231 y ambos regímenes A1/A2 =12 mundos; comparar memoria
original de entrenamiento y cargada de archivo, con control sin memoria.
Igualdad del100% de acciones/observaciones/resultados y head sin cambios,
consultas/hits positivos. Los tres brazos tienen el mismo presupuesto original.
No seleccionar mundos por score ni presentar esto como un experimento nuevo
de ventaja o un examen. Resultado, trazas y hashes en `agent-integration/`
fuera del manifiesto de formato ya cerrado. Usar entorno MiniGrid existente;
sin instalaciones. Prueba de wrapper antes de implementar, después suite
de integración y auditoría offline sin repetir mundos.
