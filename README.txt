========================================
  NXR NUKER PROTOCOL — README
========================================

Files in this package:
  nxr_nuker_protocol.py   main program
  config.yml              runtime defaults
  requirements.txt        pip dependencies
  README.txt              this file

----------------------------------------
 1. Install
----------------------------------------

  python -m pip install -r requirements.txt

----------------------------------------
 2. Configure
----------------------------------------

  Edit config.yml. Every value under nuker:
  becomes the menu default. Press ENTER at a
  prompt to accept.

  ui: controls the gradient banner and
  accent colours. Set truecolor: false for
  a plain 16-colour fallback.

----------------------------------------
 3. Run
----------------------------------------

  python nxr_nuker_protocol.py

  You will be asked for:
    - bot token
    - guild id

  Then the action menu appears.

----------------------------------------
 4. Build a standalone .exe
----------------------------------------

  pyinstaller --onefile --console ^
      --name "NXR_NUKER_PROTOCOL" ^
      --add-data "config.yml;." ^
      nxr_nuker_protocol.py

  On Linux/macOS swap ^ for \ and use
  "config.yml:." (colon).

  The exe lands in ./dist/. config.yml
  sits next to it.

----------------------------------------
 5. Bot permissions
----------------------------------------

  Ban Members, Kick Members, Manage Channels,
  Manage Roles, Manage Guild, Manage Emojis.

  Bot's highest role must sit ABOVE the roles
  it deletes, and above members it bans.

----------------------------------------
 6. Notes
----------------------------------------

  - Discord REST v10 direct.
  - 429 responses handled via retry_after.
  - PUT /bans/{id} is idempotent.
  - For self-token, strip the "Bot " prefix
    from Authorization in NXRNuker.__init__.

========================================
