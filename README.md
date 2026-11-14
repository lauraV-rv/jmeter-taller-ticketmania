# Taller de JMeter - Tiquetmania

Monorepo con la API de Tiquetmania, el plan de JMeter del despliegue y el ejercicio de experimentación "¿Qué pasaría si...?". Pruebas de software, taller de rendimiento.

## Estructura

```
api/                          API simple de Tiquetmania (Python, puerto 8080)
pruebas/jmeter/               Plan del despliegue: Ticketmania.jmx y datos.csv
pruebas/experimentacion/      Planes de las 10 preguntas, datos y resultados
.github/workflows/            Pipeline de GitHub Actions (rendimiento.yml)
entregables/                  Documentos de Word de la segunda y la tercera nota
```

## Ejercicio 1: despliegue en el pipeline

El plan `pruebas/jmeter/Ticketmania.jmx` simula el flujo de compra: consulta de tarifas, selección de tarifa y cantidad (tomadas de `datos.csv`) y pago de la reserva. El número de reserva se extrae con un Extractor JSON y el pago se valida con una Aserción JSON (`estado = APROBADO`).

Escenario: Grupo de Hilos estándar con 200 usuarios, subida de 300 segundos, contador del bucle en 1 y Temporizador Aleatorio Uniforme de 500 a 1500 ms. El CSV se lee con ruta relativa (`datos.csv`).

El workflow `rendimiento.yml` corre en cada push a `main` o a mano. En un solo job instala Java 17 y JMeter 5.6.3, levanta la API, espera a que `/api/salud` responda, ejecuta el plan en modo no-GUI, revisa el `.jtl` (si hay peticiones fallidas el job queda en rojo) y sube el reporte HTML como artefacto `reporte-rendimiento`, aunque un paso anterior haya fallado.

Ejecución local, desde `pruebas/jmeter`:

```bash
python api/ticketmania_simple.py
jmeter -n -t Ticketmania.jmx -l resultados.jtl -e -o reporte
```

## Ejercicio 2: experimentación

En `pruebas/experimentacion` hay un plan por pregunta (`P01` a `P10`). Cada plan deja fijo el escenario y expone como propiedad la única variable que cambia entre corridas (por ejemplo `-Jusuarios=20` y `-Jusuarios=500`). El script `ejecutar_experimentos.ps1` reinicia la API antes de cada corrida, ejecuta JMeter en modo no-GUI y guarda el reporte HTML en `resultados/<corrida>/reporte`. Los planes de estrés y recursos usan los plugins jpgc (Ultimate Thread Group, Transactions per Second y PerfMon con ServerAgent en el puerto 4444). Este ejercicio no lo ejecuta el pipeline.

Las respuestas, los escenarios, las capturas y las limitaciones están en `entregables/`.
