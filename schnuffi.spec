# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

viewer_files = [
                ('ui/pos_schnuffi_res.py', 'ui'),
                ('ui/schnuffi_res_paths.json', 'ui'),
                ('ui/*.ui', 'ui'),
                ('locale/de/LC_MESSAGES/*.mo', 'locale/de/LC_MESSAGES'),
                ('locale/en/LC_MESSAGES/*.mo', 'locale/en/LC_MESSAGES'),
                ]

local_hooks = ['hooks']

a = Analysis(['schnuffi.py'],
             pathex=['E:\\PycharmProjects\\PosSchnuffi'],
             binaries=[],
             datas=viewer_files,
             hiddenimports=[],
             hookspath=local_hooks,
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
          [],
          exclude_binaries=True,
          name='PosSchnuffi',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          console=False )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               upx_exclude=[],
               name='PosSchnuffi')
