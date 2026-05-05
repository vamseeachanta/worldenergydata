# Custom Slash Commands

> **⚠ This document describes custom agent slash commands (e.g. `/git-sync`), NOT the
> `worldenergydata` runtime CLI.** For runtime CLI usage (`worldenergydata bsee ...`,
> `worldenergydata fdas ...`, etc.) see [CLI.md](CLI.md).

Last updated: 2025-08-12 06:26
Propagated from: assetutilities

## Available Commands

### `/git-sync`
Local Slash Commands for Git Operations

### `/git-trunk-flow`
Git Trunk-Based Development Flow Command

### `/modernize-deps`
This command modernizes dependency management and improves module structure

### `/organize-structure`
This command organizes Python projects into a clean module-based structure,

### `/propagate-commands`
This command transfers custom slash commands from a source repository

## Usage

```bash
# List all available commands
./slash_commands.py --list

# Execute a specific command
./slash_commands.py /modernize-deps

# Get help for a command
./slash_commands.py /modernize-deps --help
```

## Adding New Commands

Place new command files in `.agent-os/commands/` directory.
Use `/propagate-commands` to distribute to other repositories.
