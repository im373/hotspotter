if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support()
    print('__main__ = gui.py')
    app, is_root = init_qtapp()
    front = make_dummy_main_window()
    run_main_loop(app, is_root, front)
