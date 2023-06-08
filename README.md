# rmfile

Remove files based on pattern

## Usage

``` shell
❯ rmfile --help

 Usage: rmfile [OPTIONS] LOCATION

 Remove files based on patterns.

╭─ Arguments ──────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *    location      TEXT  The dir or file to remove. [default: None] [required]                                       │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --name                      TEXT  Load name patterns from file [default: None]                                       │
│ --iname                     TEXT  Same as --name, but case-insensitive [default: None]                               │
│ --sha1                      TEXT  Load sha1 patterns from file [default: None]                                       │
│ --gcid                      TEXT  Load gcid patterns from file [default: None]                                       │
│ --from-dir                  TEXT  Load patterns from dir (e.g. sha1.txt) [env var: RMFILE_FROM_DIR] [default: None]  │
│ --dry-run                                                                                                            │
│ --add                             add patterns to file from dir                                                      │
│ --install-completion              Install completion for the current shell.                                          │
│ --show-completion                 Show completion for the current shell, to copy it or customize the installation.   │
│ --help                            Show this message and exit.                                                        │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

Allow patterns are:

- `name`: case-sensitive filename
- `iname`: case-insensitive filename
- `sha1`
- `gcid`

They are match with **AND** operation.

### Environment Variables

- `RMFILE_FROM_DIR`: for `--from-dir`
