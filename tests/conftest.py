def pytest_configure():
    from addok import hooks
    import addok_csv
    hooks.register(addok_csv)
