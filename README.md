# TLDR Digest Extractor

Mini-proyecto para extraer artículos de newsletters TLDR a partir de URLs `View Online`, limpiar sponsors/ads, deduplicar y producir un JSON estructurado que luego ChatGPT/OpenAI puede convertir en resumen editorial.

## Objetivo

Evitar depender del cuerpo truncado de Outlook/Gmail. El flujo recomendado es:

```text
Gmail / Outlook
  -> extraer URLs View Online
  -> ejecutar extractor sobre esas URLs
  -> obtener JSON de artículos
  -> pasar JSON a ChatGPT/OpenAI para resumen final
```

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Uso básico

```bash
python src/extract_tldr.py \
  --url "https://a.tldrnewsletter.com/web-version?..." \
  --url "https://a.tldrnewsletter.com/web-version?..." \
  --out output/articles.json \
  --log-level INFO
```

Por defecto el extractor:

- resuelve `links.tldrnewsletter.com` a la URL final del artículo;
- elimina params de tracking comunes;
- excluye sponsors del JSON final;
- deduplica noticias repetidas entre newsletters por URL canónica y por similitud temática del título/resumen.

## Qué devuelve

Un JSON con esta estructura:

```json
{
  "generated_at": "2026-06-10T12:00:00Z",
  "newsletters": [
    {
      "source": "TLDR AI",
      "date": "2026-06-09",
      "view_online_url": "...",
      "articles": [
        {
          "title": "OpenAI Filed a Confidential S-1",
          "url": "https://...",
          "summary": "OpenAI announced...",
          "section": "Headlines & Launches",
          "reading_time": "1 minute read",
          "is_sponsor": false
        }
      ]
    }
  ]
}
```

## Siguiente paso

1. Probar con dos URLs `View Online` reales.
2. Ajustar parser si TLDR cambia el HTML.
3. Conectar con Gmail/Apps Script/n8n/GitHub Actions.
4. Pasar el JSON a OpenAI/ChatGPT para selección editorial y resumen final.
