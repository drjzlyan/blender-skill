$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($args.Count -eq 0) {
    $args = @("setup", "--harness", "auto")
}
python3 "$Root/scripts/blender_skill.py" @args
exit $LASTEXITCODE
