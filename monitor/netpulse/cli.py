"""NetPulse command-line interface."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from .config import ConfigError, load_config
from .demo import build_demo_state
from .notifications import deliver_pending
from .public_data import write_public_data
from .runner import run_checks
from .state import atomic_write_json, load_state, update_state


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="netpulse", description="Monitoramento serverless NetPulse")
    commands = root.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate-config", help="Valida o YAML sem acessar a rede")
    validate.add_argument("--config", required=True)

    check = commands.add_parser("check", help="Executa monitores e atualiza o estado")
    check.add_argument("--config", required=True)
    check.add_argument("--state", required=True)
    check.add_argument("--output", required=True)
    check.add_argument("--summary-telegram", action="store_true")

    demo = commands.add_parser("demo", help="Gera dados determinísticos de demonstração")
    demo.add_argument("--output", required=True)
    return root


async def command_check(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    state, recovered_invalid = load_state(args.state)
    if recovered_invalid:
        print(
            "Aviso: estado anterior inválido; iniciando estado vazio sanitizado.", file=sys.stderr
        )
    results = await run_checks(config)
    update_state(state, config, results)
    errors = await deliver_pending(state, config, summary=args.summary_telegram)
    for error in errors:
        print(f"Aviso: {error}", file=sys.stderr)
    # State is private and is persisted before deriving public output.
    atomic_write_json(args.state, state)
    write_public_data(args.output, state, config)
    up = sum(result.success for result in results)
    print(f"Verificações concluídas: {up}/{len(results)} responderam com sucesso.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "validate-config":
            config = load_config(args.config)
            print(f"Configuração válida: {len(config.monitors)} monitor(es).")
            return 0
        if args.command == "demo":
            state, config = build_demo_state()
            write_public_data(Path(args.output), state, config, demo=True)
            print(f"Dados de demonstração gerados em {args.output}.")
            return 0
        return asyncio.run(command_check(args))
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Execução interrompida.", file=sys.stderr)
        return 130
    except Exception as exc:  # top-level CLI boundary; never prints a stack trace publicly
        print(f"Falha interna do NetPulse: {type(exc).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
