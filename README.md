# Académica SIIUAM

Sistema de extracción de datos para el sistema Académica. Extrae datos de SIIUAM (Sistema Integral de Información UAM).

## Fase 1:

* Extracción de listas de grupos.
* Serialización JSON.
* Enviar a API/Base de datos.

## Runner automático

El archivo [run_all_courses.py](run_all_courses.py) ejecuta el scraper de forma programática para múltiples UEA sin usar selección manual por consola.

Uso base:

```bash
python3 run_all_courses.py --name NOMBRE_CARPETA
```

Esto crea (o reutiliza) la carpeta indicada en `--name`, ejecuta la extracción y guarda un resumen al final en `run_summary.json`.

### Parámetros

| Parámetro | Tipo | Requerido | Default | Descripción |
|---|---|---|---|---|
| `--name` | string | Sí | - | Carpeta raíz donde se guardan resultados y resumen de la corrida. |
| `--retry-failed-from` | string (ruta) | No | - | Reintenta solo índices fallidos leyendo un `run_summary.json` previo. |
| `--only-indices` | string | No | - | Ejecuta solo los índices indicados, separados por coma. Ejemplo: `1,3,7`. |
| `--max-retries` | int | No | `3` | Número máximo de intentos por índice cuando hay error. Debe ser >= 1. |
| `--retry-delay` | float | No | `4.0` | Segundos de espera entre intentos fallidos. Debe ser >= 0. |
| `--ui-settle-seconds` | float | No | `1.5` | Espera previa antes de abrir una UEA para estabilizar la interfaz. Debe ser >= 0. |

Notas importantes:

* `--retry-failed-from` y `--only-indices` son modos alternativos de selección de índices.
* Si no se usa ninguno de esos dos parámetros, el script intenta ejecutar todos los índices disponibles (`0..N-1`).

### Ejemplos comunes

Ejecutar todos los cursos detectados:

```bash
python3 run_all_courses.py --name TDCSH
```

Ejecutar solo un índice específico:

```bash
python3 run_all_courses.py --name TDCSH --only-indices 1
```

Ejecutar varios índices concretos:

```bash
python3 run_all_courses.py --name TDCSH --only-indices 1,4,8
```

Reintentar solo los fallidos desde un resumen previo:

```bash
python3 run_all_courses.py --name TDCSH --retry-failed-from TDCSH/run_summary.json
```

Reintentos más agresivos para sesiones inestables:

```bash
python3 run_all_courses.py --name TDCSH --only-indices 1 --max-retries 5 --retry-delay 6 --ui-settle-seconds 3
```

### Salida de resumen

Al finalizar, el script guarda [run_summary.json](run_summary.json) en la carpeta de salida con estos datos:

* `generated_at`: fecha y hora de generación.
* `output_root`: ruta absoluta de salida.
* `total_courses`: total de índices ejecutados en esa corrida.
* `indices_executed`: lista de índices ejecutados.
* `successful`: cantidad de ejecuciones exitosas.
* `failed`: cantidad de ejecuciones fallidas.
* `results`: detalle por índice (estado, error, intentos, nombre de curso).
