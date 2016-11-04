def pytest_configure():
    from addok import hooks
    from addok_csv import plugin
    hooks.register(plugin)
