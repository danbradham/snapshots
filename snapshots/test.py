# Standard library imports
import sys

# Local imports
from snapshots.vendor.Qt import QtWidgets
from snapshots.ui import Sync


def main():
    app = QtWidgets.QApplication()
    sync = Sync()
    sync.set_options(
        src='//ny-media/bns_library/Pipeline/shared/nuke/toolsets',
        dst='//la-media/bns_library/Pipeline/shared/nuke/toolsets',
        replace_changed=True,
        delete_files=True,
        dry=True,
        mode=0,
    )
    sync.set_auto_accept(True)
    sync.set_auto_report(True)
    sys.exit(sync.exec_())


if __name__ == "__main__":
    main()
