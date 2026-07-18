# NetPulse Monitor

NetPulse executa verificações assíncronas em Python pelo GitHub Actions, persiste o estado em JSON e publica um painel Vue/Vite estático no GitHub Pages.

## Diretórios

- `config/`: monitores públicos versionados em YAML.
- `monitor/netpulse/`: checks, estado, histórico, alertas e CLI.
- `frontend/`: painel Vue e contratos TypeScript.
- `tests/`: testes Python sem acesso real à rede.
- `scripts/`: restauração e validação dos dados publicados.

## Comandos

```bash
python -m pip install -e ".[dev]"
python -m netpulse.cli validate-config --config config/monitors.yml
ruff check . && ruff format --check . && pytest
cd frontend && npm ci && npm run lint && npm run test -- --run && npm run build
```

Mantenha compatibilidade com o subcaminho do GitHub Pages e use `import.meta.env.BASE_URL`. Nunca coloque segredos no código, YAML, logs ou JSON público. Nunca desative a validação TLS. Toda mudança de comportamento precisa de teste.

Uma tarefa só está pronta quando configuração e JSONs validam, testes e lint passam, o frontend compila e nenhum dado sensível ou artefato local foi incluído.
