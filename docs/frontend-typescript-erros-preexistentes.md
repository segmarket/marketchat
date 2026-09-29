# Erros de TypeScript preexistentes no gate `npm run build`

Status em 2026-09-29: **o gate `npm run build` (`tsc -b && vite build`) falha** com exit 1, tanto no commit base `cdf496e` quanto no working tree com a proteção de mídia. A lista de erros é idêntica nos dois (9 erros, `diff` vazio). Como o `tsc -b` falha, o `vite build` não chega a rodar.

O `front-end/Dockerfile` usa `npx vite build` direto, ou seja, a imagem de produção **não** passa pelo type-check. `vite build` isolado não é critério de sucesso deste gate.

| # | Arquivo:linha | Código | Mensagem (resumo) | Introduzido em |
|---|---|---|---|---|
| 1 | `src/components/marketing/CookieConsentBanner.tsx:6` | TS6133 | `getConsentPreferences` importado e não usado | `f3c8daad` (2026-06-09) |
| 2 | `src/features/signup/schema.ts:11` | TS2769 | `z.literal(true, { errorMap })`: `errorMap` não existe na API do Zod 4 (`^4.4.3`) | `f3c8daad` (2026-06-09) |
| 3 | `src/layout/AppSidebar.tsx:87` | TS6133 | `secondaryNavItems` declarado e não usado | `29a0645b` (2026-06-07) |
| 4–5 | `src/constants/socialShare.ts:22`, `:27` | TS2339 | `import.meta.env` inexistente em `ImportMeta` | `f1f6804f` (2026-05-31) |
| 6–8 | `src/constants/socialShare.ts:29` (2×), `:30` | TS2304 | `window` não encontrado | `f1f6804f` (2026-05-31) |
| 9 | `vite.config.ts:59` | TS2580 | `process` não encontrado (faltam tipos do Node) | `ec7d3cca` (2026-05-17) |

## Causas prováveis e correções sugeridas (não aplicadas)

- **1 e 3:** remover o import e a constante não usados (ou usá-los).
- **2:** no Zod 4, trocar `{ errorMap: ... }` por `{ error: "mensagem" }` (ou `{ message: ... }`).
- **4 a 9:** o `vite.config.ts` importa `./src/constants/socialShare`, então esse arquivo é checado pelo `tsconfig.node.json` (`lib: ["ES2023"]`, sem `DOM`, sem `vite/client`, sem `@types/node`). Opções:
  - instalar `@types/node` como devDependency e adicionar `"types": ["node"]` ao `tsconfig.node.json`;
  - mover as constantes puras (sem `window`/`import.meta.env`) para um módulo separado importado pelo `vite.config.ts`, deixando a parte de browser só no app.

## Como reproduzir

```bash
cd front-end && npm run build; echo "exit=$?"
```
