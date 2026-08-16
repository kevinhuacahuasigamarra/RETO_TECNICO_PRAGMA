# Resultados esperados con los CSV entregados

Estos valores fueron calculados directamente a partir de los archivos originales
para poder comprobar la ejecución.

## Observación de calidad de datos

- `2012-1.csv`: 22 filas; 2 valores `price` nulos.
- `2012-4.csv`: 30 filas; 2 valores `price` nulos.
- Los otros archivos no contienen `price` nulos.
- En total antes de `validation.csv` existen 143 filas y 139 valores de precio no nulos.
- SQL Server `COUNT(*)` cuenta las filas con precio nulo.
- SQL Server `AVG(price)`, `MIN(price)`, `MAX(price)` y `COUNT(price)` ignoran los `NULL`.

## Acumulado después de cada archivo

| Archivo | Filas acumuladas | Price no nulos | SUM(price) | AVG(price) | MIN | MAX |
|---|---:|---:|---:|---:|---:|---:|
| 2012-1.csv | 22 | 20 | 1193 | 59.650000 | 14 | 97 |
| 2012-2.csv | 51 | 49 | 2783 | 56.795918 | 10 | 100 |
| 2012-3.csv | 82 | 80 | 4633 | 57.912500 | 10 | 100 |
| 2012-4.csv | 112 | 108 | 6240 | 57.777778 | 10 | 100 |
| 2012-5.csv | 143 | 139 | 8046 | 57.884892 | 10 | 100 |
| validation.csv | 151 | 147 | 8380 | 57.006803 | 10 | 100 |

## Antes de validation.csv

```text
COUNT(*)     = 143
COUNT(price) = 139
SUM(price)   = 8046
AVG(price)   ≈ 57.8848920863
MIN(price)   = 10
MAX(price)   = 100
```

## Después de validation.csv

```text
COUNT(*)     = 151
COUNT(price) = 147
SUM(price)   = 8380
AVG(price)   ≈ 57.0068027211
MIN(price)   = 10
MAX(price)   = 100
```

El programa compara automáticamente la estadística incremental con una consulta
directa a `dbo.transactions`. Si no coinciden, finaliza con error.
