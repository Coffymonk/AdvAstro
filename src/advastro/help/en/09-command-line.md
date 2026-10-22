<!-- id: cli -->
# Command line

The `advastro` command does the same analysis without a window, for batch work and scripts.
Run `advastro --help` or `advastro <command> --help` for every option.

<!-- id: cli.analyze -->
## advastro analyze

```
advastro analyze FOLDER [options]
```

| Option | Meaning |
| --- | --- |
| `-f table / json / csv` | Output format (default: a table) |
| `-o FILE` | Write the report to a file |
| `-r` | Include subfolders |
| `-j N` | Parallel workers |
| `--advise` | Identify the target and print a processing workflow |
| `--tool pixinsight / siril` | Program for the workflow |
| `--workflow FILE` | Also save the workflow as Markdown |
| `--solve` / `--no-solve` | Always / never run ASTAP when the files carry no solution |
| `--no-calibration` | Skip the calibration frames |
| `--session FILE` | A `.mksession` file (found automatically otherwise) |
| `-q` | No progress output |

Examples:

```
advastro analyze D:\Astro\2026-10-14\LIGHT
advastro analyze ./lights -f csv -o subs.csv
advastro analyze ./lights --advise --tool siril --workflow siril.md
advastro analyze ./session/DARK
```

<!-- id: cli.rate -->
## advastro rate

```
advastro rate PICTURE [options]
```

| Option | Meaning |
| --- | --- |
| `-f table / markdown / json` | Output format |
| `-o FILE` | Write the report to a file |
| `--pdf FILE` | Also write a PDF report (desktop package only) |
| `--sky` | Plate solve, measure depth against Gaia and check star colours |
| `--object NAME` | Object name, helps plate solving |
| `--tool pixinsight / siril` | Show steps for one program only |
| `--skill beginner / intermediate / advanced` | Judge at this level |
| `--type galaxy / emission / reflection / planetary / dark / cluster / globular / milkyway` | Object type (default: from the name or the plate solve) |
| `--starless auto / yes / no` | Whether the picture is starless (default: detect) |
| `--workflow` | Print the processing workflow for the object type instead of the rating |

```
advastro rate final.tif
advastro rate final.jpg --sky --object "NGC 7000" --pdf rating.pdf
advastro rate final.xisf -f markdown --tool siril -o forum-post.md
advastro rate m31.tif --type galaxy --workflow --tool pixinsight -o m31-workflow.md
```

<!-- id: cli.other -->
## Other commands

| Command | Does |
| --- | --- |
| `advastro solve FILE` | Plate solve one image and name what it shows |
| `advastro astap` | Show where ASTAP and its star databases were found |
| `advastro config [FOLDER]` | Show the merged settings and their sources |

Options for every command: `--config FILE`, `--set section.key=value`, `--no-user-config`
and `--lang en/sv`.
