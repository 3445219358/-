"""将 Windows 原生程序与操作文档打包。"""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root = Path(__file__).resolve().parent.parent
executable = root / 'dist/TaixuAscension.exe'
if not executable.is_file():
    raise SystemExit('Missing dist/TaixuAscension.exe; build it first.')

target = root / 'dist/TaixuAscension-Windows.zip'
documents = [root / 'README.md', root / 'VERSION']
documents.extend(sorted((root / 'docs').rglob('*')))
with ZipFile(target, 'w', ZIP_DEFLATED, compresslevel=6) as archive:
    archive.write(executable, executable.name)
    for document in documents:
        if document.is_file():
            archive.write(document, document.relative_to(root).as_posix())
with ZipFile(target) as archive:
    invalid = archive.testzip()
    if invalid:
        raise SystemExit(f'ZIP integrity check failed: {invalid}')
print(f'Created: {target.name} ({target.stat().st_size} bytes)')
