# PRAGMA – Prueba de Ingeniería de Datos

## Solución

Pipeline de datos en **Python + SQL Server** que procesa los archivos CSV mediante
**micro-batches**, persiste las transacciones y mantiene estadísticas incrementales
sin volver a consultar el histórico para actualizarlas.

La interfaz gráfica recomendada para revisar la base es **SQL Server Management
Studio (SSMS)**.

## Qué demuestra la solución

- Lectura incremental con `pandas.read_csv(..., chunksize=N)`.
- Nunca se cargan simultáneamente los 5 CSV en memoria.
- Inserción en SQL Server.
- `COUNT`, `SUM`, `AVG`, `MIN` y `MAX` mantenidos incrementalmente.
- El promedio se calcula mediante `SUM acumulado / COUNT(price) acumulado`.
- Los datos históricos no se vuelven a leer para actualizar estadísticas.
- Manejo correcto de `price = NULL`.
- Trazabilidad por archivo.
- Historial por micro-batch.
- Idempotencia: un archivo ya procesado no se vuelve a insertar.
- Transacción por archivo: ante error, se hace rollback completo del archivo.
- Comparación automática contra una consulta real en SQL Server.
- `validation.csv` atraviesa exactamente el mismo pipeline.

---

# 1. Requisitos en Windows

Necesitas:

1. Python 3.
2. SQL Server Express, Developer o una instancia de SQL Server a la que tengas acceso.
3. SQL Server Management Studio (SSMS), para mostrar la interfaz gráfica.
4. Un driver ODBC para SQL Server.

> `main.py` intenta detectar automáticamente un driver ODBC compatible.

---

# 2. Configurar el servidor

Abre:

```text
config.ini
```

Por defecto está preparado para:

```ini
server = localhost\SQLEXPRESS
database = PragmaDataChallenge
trusted_connection = yes
```

Si en SSMS te conectas, por ejemplo, a:

```text
DESKTOP-ABC123\SQLEXPRESS
```

entonces cambia la línea a:

```ini
server = DESKTOP-ABC123\SQLEXPRESS
```

Si tu servidor aparece solo como:

```text
localhost
```

usa:

```ini
server = localhost
```

No necesitas colocar usuario ni contraseña cuando usas autenticación de Windows.

---

# 3. Ejecución más sencilla

Haz doble clic en:

```text
run_demo.bat
```

El archivo realiza automáticamente:

1. Crea `.venv`.
2. Instala `pandas` y `pyodbc`.
3. Ejecuta la prueba unitaria.
4. Crea `PragmaDataChallenge` si no existe.
5. Crea las tablas.
6. Limpia una ejecución anterior.
7. Procesa `2012-1.csv` a `2012-5.csv`.
8. Comprueba las estadísticas contra SQL Server.
9. Procesa `validation.csv` mediante el mismo pipeline.
10. Vuelve a comprobar las estadísticas.

---

# 4. Ejecución manual

Desde PowerShell o CMD, en la carpeta del proyecto:

```bat
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python main.py --reset
```

`--reset` se usa para una demostración limpia.

Para ejecutar nuevamente sin borrar datos:

```bat
python main.py
```

Los archivos ya cargados aparecerán como:

```text
[SKIP] 2012-1.csv ya fue procesado anteriormente.
```

Esto demuestra idempotencia.

---

# 5. Verlo gráficamente en SSMS

Cuando termine `run_demo.bat`:

1. Abre SQL Server Management Studio.
2. Conéctate al mismo servidor configurado en `config.ini`.
3. En **Databases**, actualiza con `Refresh`.
4. Abre:

```text
PragmaDataChallenge
  └── Tables
      ├── dbo.transactions
      ├── dbo.processed_files
      ├── dbo.pipeline_statistics
      └── dbo.statistics_history
```

5. En SSMS abre el archivo:

```text
sql\02_validation_queries.sql
```

6. Pulsa **Execute**.

---

# 6. Diseño de tablas

## dbo.transactions

Contiene todas las transacciones cargadas:

- `event_timestamp`
- `price`
- `user_id`
- `source_file`
- `ingested_at`

## dbo.pipeline_statistics

Mantiene UNA sola fila con el estado acumulado:

- `total_rows`
- `valid_price_count`
- `price_sum`
- `avg_price`
- `min_price`
- `max_price`

La actualización de esta tabla usa únicamente:

```text
estadística anterior + nuevo micro-batch
```

No ejecuta `AVG(price)` sobre todo el histórico para actualizarse.

## dbo.statistics_history

Guarda una fotografía de las estadísticas después de cada micro-batch.

## dbo.processed_files

Registra los archivos completados y permite evitar duplicados.

---

# 7. Por qué existen total_rows y valid_price_count

Los archivos entregados contienen cuatro filas cuyo `price` es nulo:

- dos en `2012-1.csv`;
- dos en `2012-4.csv`.

El requisito solicita contar filas cargadas y calcular estadísticas del campo `price`.

Por eso:

```text
total_rows
```

cuenta todas las filas cargadas, mientras:

```text
valid_price_count
```

representa el número de precios usados para el promedio.

Esto equivale en SQL Server a:

```sql
COUNT(*)       -- todas las filas
COUNT(price)   -- precios no NULL
AVG(price)     -- ignora NULL automáticamente
```

No se eliminan las filas con precio nulo.

---

# 8. Fórmula incremental

Para un micro-batch nuevo:

```text
new_total_rows = old_total_rows + batch_rows

new_price_count =
    old_price_count + batch_valid_price_count

new_sum =
    old_sum + batch_sum

new_avg =
    new_sum / new_price_count

new_min =
    min(old_min, batch_min)

new_max =
    max(old_max, batch_max)
```

Así no es necesario volver a recorrer las transacciones anteriores.

---

# 9. Micro-batch

En `config.ini`:

```ini
chunk_size = 1
```

Esto significa que, para esta prueba, Pandas procesa **una fila por iteración**. Así las estadísticas se actualizan inmediatamente después de cada fila insertada, que es el nivel ideal sugerido por el enunciado.

En un escenario real podrías aumentar este valor, por ejemplo:

```ini
chunk_size = 1000
```

sin cambiar el código. Para la demostración técnica se deja en `1` para mostrar la actualización fila por fila.

---

# 10. Comprobación exigida por el reto

Después de los cinco archivos principales, `main.py` ejecuta una consulta independiente:

```sql
SELECT
    COUNT(*) AS total_rows,
    COUNT(price) AS valid_price_count,
    SUM(price) AS price_sum,
    AVG(price) AS avg_price,
    MIN(price) AS min_price,
    MAX(price) AS max_price
FROM dbo.transactions;
```

La consulta se utiliza **solo como comprobación**, no para mantener las estadísticas.

Luego `validation.csv` pasa por el mismo pipeline y se repite la comprobación.

---

# 11. Resultados esperados

Antes de `validation.csv`:

```text
total_rows        = 143
valid_price_count = 139
price_sum         = 8046
avg_price         ≈ 57.8848920863
min_price         = 10
max_price         = 100
```

Después de `validation.csv`:

```text
total_rows        = 151
valid_price_count = 147
price_sum         = 8380
avg_price         ≈ 57.0068027211
min_price         = 10
max_price         = 100
```

Consulta `EXPECTED_RESULTS.md` para ver el acumulado por archivo.

---

# 12. Qué mostrar durante la sustentación

Orden recomendado:

1. Enseñar la estructura del proyecto.
2. Explicar `chunksize`.
3. Ejecutar `run_demo.bat`.
4. Mostrar cómo las estadísticas cambian con cada micro-batch.
5. Abrir SSMS.
6. Mostrar `dbo.transactions`.
7. Mostrar `dbo.pipeline_statistics`.
8. Mostrar `dbo.statistics_history`.
9. Ejecutar `sql\02_validation_queries.sql`.
10. Mostrar que el resultado SQL coincide con el acumulado.
11. Explicar que la consulta global se usa solo para validar, no para actualizar.
12. Ejecutar nuevamente sin reset para demostrar idempotencia.

---

# 13. Estructura

```text
pragma_sqlserver_challenge/
│
├── data/
│   ├── 2012-1.csv
│   ├── 2012-2.csv
│   ├── 2012-3.csv
│   ├── 2012-4.csv
│   ├── 2012-5.csv
│   └── validation.csv
│
├── sql/
│   ├── 01_create_database_and_schema.sql
│   ├── 02_validation_queries.sql
│   └── 03_reset.sql
│
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── pipeline.py
│   └── statistics.py
│
├── tests/
│   └── test_statistics.py
│
├── config.ini
├── EXPECTED_RESULTS.md
├── main.py
├── README.md
├── requirements.txt
├── run_demo.bat
└── run_idempotent.bat
```
