# HotSpotter port notes:
# Stores menu source strings with Qt translation no-op markers.


from PyQt5.QtCore import QT_TRANSLATE_NOOP


MENU_CONTEXT = 'HotSpotterMenus'


MENU_TEXT = {
    # File menu
    'new_database': QT_TRANSLATE_NOOP('HotSpotterMenus', 'New Database'),
    'open_database': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Open Database'),
    'save_database': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Save Database'),
    'import_img_file': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Import Images (select file(s))'),
    'import_img_dir': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Import Images (select directory)'),
    'quit': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Quit'),

    # View menu
    'layout_figures': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Layout Figures'),
    'filter_table': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Filter Table'),
    'clear_filter': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Clear Filter'),

    # Actions menu
    'add_chip': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Add Chip'),
    'new_chip_property': QT_TRANSLATE_NOOP('HotSpotterMenus', 'New Chip Property'),
    'query': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Query'),
    'reselect_roi': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Reselect ROI'),
    'reselect_ori': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Reselect Orientation'),
    'previous': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Select Previous'),
    'next': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Select Next'),
    'previous_unannotated': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Select Previous Unannotated'),
    'next_unannotated': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Select Next Unannotated'),
    'delete_chip': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Delete Chip'),
    'delete_image': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Trash Image'),
    'clean_name_table': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Clean Name Table'),

    # Batch menu
    'precompute_chips_features': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Precompute Chips/Features'),
    'precompute_queries': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Precompute Queries'),
    'scale_all_rois': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Scale all ROIs'),
    'convert_all_images_into_chips': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Convert all images into chips'),

    # Options menu
    'preferences': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Edit Preferences'),

    # Help menu
    'about': QT_TRANSLATE_NOOP('HotSpotterMenus', 'About'),
    'view_docs': QT_TRANSLATE_NOOP('HotSpotterMenus', 'View Documentation'),
    'view_dbdir': QT_TRANSLATE_NOOP('HotSpotterMenus', 'View Database Dir'),
    'view_computed_dir': QT_TRANSLATE_NOOP('HotSpotterMenus', 'View Computed Dir'),
    'view_global_dir': QT_TRANSLATE_NOOP('HotSpotterMenus', 'View Global Dir'),
    'write_logs': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Write Logs'),
    'delete_precomputed_results': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Delete Cached Query Results'),
    'delete_computed_directory': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Delete Computed Directory'),
    'delete_global_preferences': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Delete Global Preferences'),
    'dev_mode_ipython': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Developer Mode (IPython)'),
    'developer_reload': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Developer Reload'),
    'detect_duplicate_images': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Detect Duplicate Images'),
}


MENU_TOOLTIP = {
    # File menu
    'new_database': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Create a new folder to use as a database.'),
    'open_database': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Opens a different database directory.'),
    'save_database': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Saves the added images / chip properties / and changed names to the database csv tables.'),
    'quit': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Exits the program'),

    # View menu
    'layout_figures': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Organizes windows in a grid'),
    'filter_table': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Filters rows in the currently visible table.'),
    'clear_filter': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Clears filters from every table and refreshes all tables.'),

    # Actions menu
    'add_chip': QT_TRANSLATE_NOOP('HotSpotterMenus', 'When adding a chip, you select an ROI in Image View. The ROI defines a new chip and it is added (but not saved) to the database.'),
    'new_chip_property': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Creates a new column in the chip table for user properties.'),
    'query': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Issues the currently selected chip as a query. The result table is then populated.'),
    'reselect_roi': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Changes the ROI of a chip. Previously associated results and chip data are removed and recomputed.'),
    'reselect_ori': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Changes the orientation of a chip. Previously associated results and chip data are removed and recomputed.'),
    'previous': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Selects the previous image in the database.'),
    'next': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Selects the next image in the database.'),
    'previous_unannotated': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Selects the previous image without chips.'),
    'next_unannotated': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Selects the next image without chips.'),
    'delete_chip': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Removes a chip from the database.'),
    'clean_name_table': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Removes name rows with no chips from the database file.'),

    # Batch menu
    'precompute_chips_features': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Extracts all chips from images, and computes features. This loads the data into memory and reduces waiting time between selecting chips and images.'),
    'precompute_queries': QT_TRANSLATE_NOOP('HotSpotterMenus', "This might take anywhere from a coffee break to an overnight procedure depending on how many ROIs you've made. It queries each chip and saves the result which allows multiple queries to be rapidly inspected later."),
    'scale_all_rois': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Changes the size of every ROI in the database.'),
    'convert_all_images_into_chips': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Every image without a chip has an ROI added to it spanning the entire image.'),

    # Options menu
    'preferences': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Changes algorithm parameters and program behavior.'),

    # Help menu
    'view_dbdir': QT_TRANSLATE_NOOP('HotSpotterMenus', "Opens the database folder in your operating system's native file browser (explorer/finder/nautilus)"),
    'view_computed_dir': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Opens the directory where all precomputed chips, query results, and features are stored.'),
    'view_global_dir': QT_TRANSLATE_NOOP('HotSpotterMenus', 'This is your ~/.hotspotter folder, which stores non-database-specific preferences.'),
    'delete_precomputed_results': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Removes all precomputed results. Use if you expect that your results may be corrupted.'),
    'delete_computed_directory': QT_TRANSLATE_NOOP('HotSpotterMenus', 'Deletes all precomputations (not your ROIs or properties though) and lets all data be recomputed and reloaded. This puts your database in a cleaner state.'),
    'delete_global_preferences': QT_TRANSLATE_NOOP('HotSpotterMenus', 'This deletes global preferences like the previously opened database, your work directory, and defaults algorithm preferences. Use if HotSpotter crashes on loading a database.'),
    'dev_mode_ipython': QT_TRANSLATE_NOOP('HotSpotterMenus', 'This allows IPython interaction in the terminal and disables GUI interaction until the "exit" command is entered in IPython.'),
}


def text(key):
    return MENU_TEXT.get(key, key)


def tooltip(key):
    return MENU_TOOLTIP.get(key)
