import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_core_components as dcc
from dash.dependencies import Input, Output, State


class TimeControllerComponent(html.Div):
    """Controller of start time and duration for time series windows"""
    def __init__(self, parent_app, start=True, duration=True, frame=False,
                 tmin=0, tmax=1, tstart=0, tduration=1):
        super().__init__([])
        self.parent_app = parent_app
        self.tmax = tmax
        self.tmax_duration = tmax

        # Start controller'
        if start:
            self.slider_start = dcc.Slider(
                id="slider_start_time",
                min=tmin, max=tmax, value=tstart, step=0.05,
            )

            group_start = dbc.FormGroup(
                [
                    dbc.Row(
                        dbc.Col(
                            dbc.Label('start (s): ' + str(tstart), id='slider_start_label'),
                            width={'size':12},
                        ),
                    ),
                    dbc.Row(
                        dbc.Col(
                            self.slider_start,
                            width={'size': 12},
                        )
                    )
                ],
            )

            @self.parent_app.callback(
                Output(component_id='slider_start_label', component_property='children'),
                [Input(component_id='slider_start_time', component_property='value')]
            )
            def update_slider_start_label(select_start_time):
                """Updates Start slider controller label"""
                return 'start (s): ' + str(select_start_time)

        # Duration controller
        if duration:
            self.input_duration = dcc.Input(
                id="input_duration",
                type='number',
                min=.5, max=100, step=.1, value=tduration
            )

            group_duration = dbc.FormGroup(
                [
                    dbc.Row(
                        dbc.Col(
                            dbc.Label('duration (s):'), 
                            width={'size': 12}
                        )
                    ),
                    dbc.Row(
                        dbc.Col(
                            self.input_duration,
                            width={'size':12},
                        )
                    )
                ],
            )

        # Controllers main layout
        self.children = dbc.Col([
            dbc.FormGroup(
                [
                    dbc.Col(group_start, width=9),
                    dbc.Col(group_duration, width=3)
                ],
                row=True
            ),
            html.Div(id='external-update-max-time-trigger', style={'display': 'none'})
        ])

        @self.parent_app.callback(
            [Output('input_duration', 'max'), Output('slider_start_time', 'max')],
            [Input('external-update-max-time-trigger', 'children'), Input('input_duration', 'value')],
            [State('input_duration', 'value')]
        )
        def update_max_times(trigger, trigger_duration, duration):
            """
            Update max slider value when duration change
            Update max duration and max slider value when new nwb tmax are defined
            """
            duration_tmax = self.tmax
            slider_tmax = self.tmax - duration

            return duration_tmax, slider_tmax