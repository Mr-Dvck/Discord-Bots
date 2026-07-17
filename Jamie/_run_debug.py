import traceback, sys, asyncio
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))
try:
    from main import main
    main()
except SystemExit as e:
    print('SystemExit', e, file=sys.stderr)
except BaseException:
    traceback.print_exc()
    raise
