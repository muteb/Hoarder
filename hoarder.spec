# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['hoarder.py'],
             pathex=['.'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries + [('msvcp140.dll', 'C:\\Windows\\System32\\msvcp140.dll', 'BINARY'),('vcruntime140_1.dll', 'C:\\Windows\\System32\\vcruntime140_1.dll', 'BINARY')],
          a.zipfiles,
          a.datas,
          [],
          name='hoarder',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True , icon='hoarder.ico')
