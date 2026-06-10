# Workflow ChatGPT <-> Codex

Este proyecto separa el trabajo en dos fases:

1. `Codex` extrae, limpia y deduplica artículos desde URLs `View Online` de TLDR.
2. `ChatGPT` recibe el JSON limpio y produce el digest editorial final en español.

## Roles

### Codex

- recibe una o más URLs `View Online`;
- descarga la versión web completa;
- elimina sponsors, ads, footer y ruido de tracking;
- resuelve URLs canónicas cuando es posible;
- deduplica artículos entre newsletters;
- produce `output/articles.json`;
- prepara un paquete de handoff listo para pegar en ChatGPT.

### ChatGPT

- recibe el prompt editorial y el JSON ya limpio;
- selecciona artículos principales y secundarios;
- redacta el digest final en español;
- preserva los resúmenes TLDR originales para los principales;
- muestra notas de extracción si el JSON incluye warnings.

## Flujo operativo

### 1. Obtener URLs `View Online`

El usuario o ChatGPT localiza las URLs `View Online` en Gmail, Outlook u otra fuente.

### 2. Ejecutar el extractor con Codex

```bash
python src/extract_tldr.py \
  --url "https://tracking.tldrnewsletter.com/..." \
  --url "https://tracking.tldrnewsletter.com/..." \
  --out output/articles.json \
  --log-level INFO
```

Salida esperada:

- `output/articles.json`
- warnings de extracción en el propio JSON si hubo problemas de resolución o parsing

### 3. Preparar el handoff a ChatGPT

```bash
python src/build_editorial_handoff.py \
  --articles output/articles.json \
  --prompt editorial_prompt.md \
  --out output/editorial_handoff.md
```

Salida esperada:

- `output/editorial_handoff.md`

Ese archivo contiene:

- instrucciones para ChatGPT;
- resumen del lote extraído;
- warnings de extracción si existen;
- el prompt editorial;
- el JSON completo embebido en un bloque listo para copiar/pegar.

### 4. Pegar el handoff en ChatGPT

Abrir `output/editorial_handoff.md`, copiar su contenido completo y pegarlo en ChatGPT.

### 5. Iterar si hay problemas

Si ChatGPT detecta:

- artículos faltantes;
- duplicados temáticos que no colapsaron bien;
- links canónicos incorrectos;
- warnings relevantes de extracción;

el siguiente paso es devolver el caso a Codex junto con:

- las URLs originales;
- `output/articles.json`;
- el digest o feedback concreto sobre qué salió mal.

## Contrato entre fases

### Entrada a Codex

- una o más URLs `View Online`

### Salida de Codex

- `output/articles.json`
- `output/editorial_handoff.md`

### Entrada a ChatGPT

- contenido completo de `output/editorial_handoff.md`

### Salida de ChatGPT

- digest final en español

## Comando mínimo recomendado

```bash
python src/extract_tldr.py --url "URL_1" --url "URL_2" --out output/articles.json
python src/build_editorial_handoff.py --articles output/articles.json --out output/editorial_handoff.md
```

## Qué queda fuera de este repo

Todavía no está automatizado aquí:

- extraer automáticamente las URLs desde Gmail/Outlook;
- enviar el handoff a ChatGPT por API;
- recoger automáticamente la respuesta editorial final.

Eso sería la siguiente capa de integración.
