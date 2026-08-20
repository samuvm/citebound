# Protocolo de latencia · `make bench`

`docs/GOALS.yaml :: G-TTFT` dice **qué** se mide y este fichero dice **cómo**. Sin él, el número
no es comparable ni consigo mismo de una semana a otra, que es exactamente lo que pasaba en
`docs/PROJECT.md`: la celda «cómo se mide» estaba literalmente en blanco.

## Qué se mide, y por qué son dos números

```
TTFS  hasta el evento `sources`      lo primero que el usuario ve
TTFT  hasta el primer evento `token` lo primero que el MODELO dice
```

**Medir el TTFT hasta `sources` sería hacer trampa.** `sources` sale tras recuperar y reordenar,
antes de que el modelo haya escrito una sola palabra: publicar ese número como «tiempo hasta el
primer token» daría un p95 excelente sobre algo que no es lo que la meta promete. Se publican
los dos, siempre, y el README lo dice con estas palabras.

## Cómo

| | |
|---|---|
| Peticiones | **60** por repetición |
| Descarte | las **5 primeras** — arranque en frío del proceso, no del sistema |
| Repeticiones | **3** completas |
| Qué se publica | el **máximo** de los tres p95, no la media |
| Transporte | `loopback`, sin proxy, `streaming` activo |
| Preguntas | del golden set, **en orden fijo**, para que dos corridas midan lo mismo |

**El máximo de los tres p95 y no la media**, y no es pesimismo: la media de tres repeticiones
esconde una que se fue, y una que se va es exactamente lo que un usuario nota. Si las tres son
parecidas, el máximo se parece a la media; si no lo son, el máximo lo dice.

**Las cinco primeras se descartan** porque el primer `predict` de MPS compila kernels y el
primer `httpx` abre el pool. Eso es arranque del proceso y no del sistema; el arranque en frío
de verdad tiene su propia meta, `G-COLD-CACHE`, y se mide aparte.

## Condiciones obligatorias

`docs/RULES.md` R11 y `docs/GOALS.yaml :: hardware_referencia`. **Un p95 sin estas condiciones
declaradas no es comparable con nada**, así que el script las comprueba donde puede y las
declara siempre en el informe:

- portátil **enchufado**;
- sin *throttling* térmico entre repeticiones;
- modelos **residentes** (`make warm`, `OLLAMA_KEEP_ALIVE >= 10m`);
- **ninguna otra carga de GPU en la máquina**.

La última es la que más se olvida y la que más mueve el número. El script mira qué hay cargado
en Ollama y avisa; lo que no puede ver —otro proceso usando la GPU— queda declarado como
supuesto en el informe, que es lo honesto cuando no se puede comprobar.

## Presupuesto por etapa

De `docs/RULES.md` §2.1. **Una etapa fuera de su presupuesto marca ámbar aunque el total pase**,
porque el margen de 210 ms es de donde vienen las regresiones de dentro de tres semanas.

| Etapa | Presupuesto p95 |
|---|---:|
| Embedding de la consulta | 40 ms |
| Búsqueda híbrida | 90 ms |
| Rerank 30 → 5 | 400 ms |
| Prefill + primer token | 700 ms |
| Overhead FastAPI/SSE | 60 ms |
| **Total** | **1.290 ms** · margen 210 |
