# Painel administrativo

O painel é um aplicativo Next.js exportado estaticamente. `basePath` e o
trailing slash são deliberadamente `/admin`; o servidor FastAPI monta o
conteúdo de `frontend/out` nesse prefixo e mantém `/api/*` fora do fallback
HTML.

```bash
npm ci
npm run typecheck
npm test
npm run build
```

Clientes HTTP ficam em `src/lib/` ou no diretório da feature. Componentes não
devem montar URLs ou interpretar erros de transporte diretamente. Tipos e
transformações específicas de música ficam em `src/features/songs/`.
