# -*- mode: python -*-

block_cipher = None
hiddenimports = []

a = Analysis(['AutoLoginGUI.py'],
             pathex=['E:\\Documents\\python\\AutoLoginGUI'],
             binaries=[],
             datas=[],
             hiddenimports=hiddenimports,
             hookspath=[],
             runtime_hooks=['RuntimeHook.py'],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
a.datas += [('login.ico', 'login.ico', 'DATA')]
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='AutoLoginGUI',
          debug=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=False,
          icon='login.ico' )

# exe = EXE(pyz,
#           a.scripts,
#           exclude_binaries=True,
#           name='AutoLoginGUI',
#           debug=False,
#           strip=False,
#           upx=True,
#           console=True )
# coll = COLLECT(exe,
#                a.binaries,
#                a.zipfiles,
#                a.datas,
#                strip=False,
#                upx=True,
#                name='AutoLoginGUI',
#                icon='login.ico')

