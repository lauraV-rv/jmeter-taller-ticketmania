# Taller de JMeter - Tiquetmania

Monorepo con la API de Tiquetmania, el plan de JMeter del despliegue y el ejercicio de experimentación "¿Qué pasaría si...?". Pruebas de software, taller de rendimiento.

## Estructura

```
api/                          API simple de Tiquetmania (Python, puerto 8080)
pruebas/jmeter/               Plan del despliegue: Ticketmania.jmx y datos.csv
pruebas/experimentacion/      Planes de las 10 preguntas, datos, scripts y resultados
.github/workflows/            Pipeline de GitHub Actions (rendimiento.yml)
entregables/                  Documentos de Word de la segunda y la tercera nota
```

## Segunda nota: plan de JMeter y despliegue en el pipeline

El plan `pruebas/jmeter/Ticketmania.jmx` simula el flujo de compra visto en clase: consulta de tarifas, selección de tarifa y cantidad (tomadas de `datos.csv`) y pago de la reserva. El número de reserva se extrae con un Extractor JSON y el pago se valida con una Aserción JSON (`estado = APROBADO`).

Escenario del despliegue: Grupo de Hilos estándar con 200 usuarios, subida de 300 segundos, contador del bucle en 1 y Temporizador Aleatorio Uniforme de 500 a 1500 ms. El CSV se lee con ruta relativa (`datos.csv`) y el plan no usa plugins, para que corra igual en GitHub Actions.

El workflow `rendimiento.yml` corre en cada push a `main` o a mano. En un solo job instala Java 17 y JMeter 5.6.3, levanta la API, espera a que `/api/salud` responda, ejecuta el plan en modo no-GUI, revisa el `.jtl` (si hay peticiones fallidas el job queda en rojo) y sube el reporte HTML como artefacto `reporte-rendimiento`, aunque un paso anterior haya fallado.

Ejecución local:

```bash
python api/ticketmania_simple.py
cd pruebas/jmeter
jmeter -n -t Ticketmania.jmx -l resultados.jtl -e -o reporte
```

## Tercera nota: experimentación "¿Qué pasaría si...?"

En `pruebas/experimentacion` hay un plan por pregunta (`P01` a `P10`). Cada plan deja fijo el escenario y expone como propiedad la única variable que cambia entre corridas (por ejemplo `-Jusuarios=20` y `-Jusuarios=500`). `ejecutar_experimentos.ps1` reinicia la API antes de cada corrida, ejecuta JMeter en modo no-GUI y guarda el reporte HTML en `resultados/<corrida>/reporte`; `analizar.py` resume las corridas en `resultados/resumen.json`. Los planes de estrés y recursos usan los plugins jpgc (Ultimate Thread Group, Transactions per Second y PerfMon con ServerAgent en el puerto 4444). El pipeline no ejecuta esta carpeta.

Hallazgos principales: la API responde en 1 a 2 ms y su throughput crece en proporción a los usuarios mientras las conexiones llegan repartidas; cuando muchos usuarios llegan en el mismo instante rechaza la mayoría de las conexiones (su cola de conexiones pendientes es de 5); y en un solo computador con Windows el primer límite son los puertos TCP (unas 130 conexiones nuevas por segundo), no la CPU ni la memoria.

Las respuestas, los escenarios, las capturas y las limitaciones están en `entregables/`.
