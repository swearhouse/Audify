from unittest.mock import patch

from audify.__main__ import main


def test_main_serves_app_on_all_interfaces_with_waitress():
    with patch("audify.__main__.serve") as serve:
        main()

    app = serve.call_args.args[0]
    assert app.name == "audify.app"
    assert serve.call_args.kwargs == {"host": "0.0.0.0", "port": 8000}
