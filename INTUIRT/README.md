# INTUIRT — simulador do modelo IRT

Página estática: `index.html` + `data/trace_*.json`. Não precisa de servidor próprio nem de build.

## Publicar no GitHub Pages
1. Crie um repositório (ex.: `INTUIRT`) e envie estes arquivos para a raiz.
2. Settings → Pages → Source: "Deploy from a branch" → branch `main`, pasta `/ (root)`.
3. Em 1–2 minutos o site fica em `https://SEU-USUARIO.github.io/INTUIRT/`.

## Testar no computador
Abrir o `index.html` com duplo clique não carrega os traces (o navegador bloqueia leitura de arquivos locais) e a página cai no porte em JavaScript. Para ver os traces do modelo Python:

    python -m http.server 8000

e acesse http://localhost:8000

## Gerar novos traces
    python exportar_intuirt.py modelo_irt BA 59 > data/trace_ba.json
    python exportar_intuirt.py modelo_irt ER 59 > data/trace_er.json
    python exportar_intuirt.py modelo_irt WS 59 > data/trace_ws.json
