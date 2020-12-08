from allen_oephys_dashboard import AllenDashboard
from flask import Flask
import dash
import dash_bootstrap_components as dbc
import dash_html_components as html


def init_dash(server):
    external_stylesheets = [dbc.themes.BOOTSTRAP]
    dash_app = dash.Dash(
        server=server,
        external_stylesheets=external_stylesheets,
        suppress_callback_exceptions=True,
        routes_pathname_prefix='/dashboard/',
    )
    dash_app.layout = html.Div(AllenDashboard(parent_app=dash_app))

    return dash_app.server


def init_flask():
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object('config.ConfigDev')

    with app.app_context():
        init_dash(server=app)

    return app


if __name__ == '__main__':
    app = init_flask()
    app.run(debug=True, use_reloader=True)