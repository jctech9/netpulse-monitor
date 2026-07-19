# NetPulse Monitor

Monitor de disponibilidade executado pelo GitHub Actions e publicado como painel estático no GitHub Pages.

[![CI](https://github.com/jctech9/netpulse-monitor/actions/workflows/ci.yml/badge.svg)](https://github.com/jctech9/netpulse-monitor/actions/workflows/ci.yml)
[![GitHub Pages](https://github.com/jctech9/netpulse-monitor/actions/workflows/monitor-and-deploy.yml/badge.svg)](https://github.com/jctech9/netpulse-monitor/actions/workflows/monitor-and-deploy.yml)
![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![Vue 3](https://img.shields.io/badge/Vue-3-42B883?style=flat-square&logo=vuedotjs&logoColor=white)

**Painel público:** [jctech9.github.io/netpulse-monitor](https://jctech9.github.io/netpulse-monitor/)

![Painel NetPulse](docs/images/netpulse-dashboard.png)

## O que ele faz

- Monitora HTTP, conteúdo, APIs JSON, TCP, DNS e certificados TLS.
- Mantém histórico, disponibilidade e incidentes sem banco de dados externo.
- Envia alertas opcionais de queda e recuperação pelo Telegram.
- Gera JSONs públicos sanitizados para um painel Vue responsivo.
- Executa automaticamente pelo GitHub Actions e publica no GitHub Pages.

```text
config/monitors.yml → GitHub Actions → Python → JSON público → Vue → GitHub Pages
```

## Executar localmente

Requer Python 3.11+ e Node.js 22+.

```bash
python -m pip install -e ".[dev]"
python -m netpulse.cli validate-config --config config/monitors.yml
python -m netpulse.cli demo --output frontend/public/data

cd frontend
npm ci
npm run dev
```

Abra a URL exibida pelo Vite.

## Configurar monitores

Os destinos públicos ficam em `config/monitors.yml`:

```yaml
schema_version: 1

settings:
  timezone: America/Sao_Paulo
  default_timeout_seconds: 8
  default_failure_threshold: 2
  default_recovery_threshold: 1
  max_concurrency: 10

monitors:
  - id: example_site
    name: Site de exemplo
    group: Web
    type: http
    url: https://example.com
    expected_status: [200]
```

Tipos disponíveis:

- `http`: status HTTP.
- `keyword`: presença ou ausência de texto.
- `json`: assertiva sobre um caminho JSON.
- `tcp`: conexão com host e porta.
- `dns`: resolução de hostname.
- `tls`: validade do certificado.

IDs devem ser únicos e usar letras minúsculas, números, `_` ou `-`. URLs não podem conter credenciais. Toda informação da configuração e do painel deve ser considerada pública.

## Testes

```bash
python -m netpulse.cli validate-config --config config/monitors.yml
ruff check .
ruff format --check .
pytest

cd frontend
npm ci
npm run lint
npm run test -- --run
npm run build
```

Os testes não acessam serviços externos; as integrações são simuladas.

## Deploy

O workflow `Monitor and deploy` executa os monitores, atualiza os dados e publica o painel.

Para ativá-lo:

1. Em **Settings → Pages**, selecione **GitHub Actions** como fonte.
2. Execute manualmente o workflow na primeira publicação.
3. Confirme o [painel](https://jctech9.github.io/netpulse-monitor/) e o [status.json](https://jctech9.github.io/netpulse-monitor/data/status.json).

## Telegram

Configure estes Secrets no GitHub apenas se quiser receber alertas:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

Nunca coloque os valores no YAML, código, logs ou JSON público.

## Segurança

- A validação TLS nunca é desativada.
- Corpos HTTP e credenciais não são publicados.
- Estado privado, caches, builds e arquivos `.env` são ignorados pelo Git.
- Os workflows usam permissões mínimas.

## Estrutura

```text
config/              configuração dos monitores
monitor/netpulse/    motor Python e CLI
frontend/            painel Vue/Vite
tests/               testes Python
scripts/             restauração e validação de dados
.github/workflows/   CI, monitoramento e deploy
```

## Licença

[MIT](LICENSE) — criado por [Jones Cabral](https://github.com/jctech9).
