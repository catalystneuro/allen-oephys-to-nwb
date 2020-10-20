from nwbwidgets.utils.timeseries import (get_timeseries_maxt, get_timeseries_mint,
                                         timeseries_time_to_ind, get_timeseries_in_units,
                                         get_timeseries_tt)
import numpy as np

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State, ALL
import dash
from pathlib import Path
import pynwb
from nwb_web_gui.dashapps.utils.make_components import FileBrowserComponent
from .components.time_controller import TimeControllerComponent
from .components.tiff_component import TiffImageSeriesComponent


class AllenDashboard(html.Div):
    """Dashboard built with Dash version of NWB widgets"""
    def __init__(self, parent_app, path_nwb=None):
        super().__init__([])
        self.parent_app = parent_app
        self.path_nwb = path_nwb
        self.photon_series = []

        # Controllers
        self.controller_time = TimeControllerComponent(
            parent_app=self.parent_app,
            start=True, duration=True, frame=False,
            tmin=0, tmax=100, tstart=0, tduration=10
        )

        self.filebrowser = FileBrowserComponent(parent_app=parent_app, id_suffix='allen-dash')

        if self.path_nwb is not None:
            self.render_dashboard()

        # Dashboard main layout
        self.children = [
            dbc.Container([
                html.Br(),
                self.filebrowser,
                html.Br(),
                dbc.Row(
                    dbc.Col(
                        id='div-controller',
                        children= dbc.Card(
                            self.controller_time,
                            style={'margin-bottom': '10px', 'max-height': '75px'}
                        ),
                        style={'display': 'none'},
                        width={'size': 12},
                    ),
                ),
                dbc.Row([
                    dbc.Col(
                        id='div-figure-traces',
                        children = dbc.Card(
                            dcc.Graph(
                                id='figure_traces',
                                figure={},
                                config={
                                    'displayModeBar': False,
                                    'edits': {
                                        'shapePosition': True
                                    }
                                }
                            ),
                            style={'padding': '30px'}
                        ),
                        style={'display': 'none'},
                        width={'size': 8}
                    ),
                    dbc.Col(
                        id='div-photon-series',
                        style={'display': 'inline-block'},
                        width={'size': 4}
                    ),
                ]),
            ], style={'min-width': '80vw'})
        ]

        self.style = {'background-color': '#f0f0f0', 'min-height': '100vh'}

        @self.parent_app.callback(
            [Output(component_id='div-figure-traces', component_property='style'), Output('figure_traces', 'figure')],
            [
                Input(component_id='slider_start_time', component_property='value'),
                Input(component_id='input_duration', component_property='value')
            ]
        )
        def update_traces(select_start_time, select_duration):

            ctx = dash.callback_context
            trigger_source = ctx.triggered[0]['prop_id'].split('.')[1]

            if not trigger_source:
                raise dash.exceptions.PreventUpdate

            time_window = [select_start_time, select_start_time + select_duration]

            # Update electrophys trace
            timeseries = self.ecephys_trace
            istart = timeseries_time_to_ind(timeseries, time_window[0])
            istop = timeseries_time_to_ind(timeseries, time_window[1])
            yy, units = get_timeseries_in_units(timeseries, istart, istop)
            xx = get_timeseries_tt(timeseries, istart, istop)
            xrange0, xrange1 = min(xx), max(xx)
            self.traces.data[0].x = xx
            self.traces.data[0].y = list(yy)
            self.traces.update_layout(
                yaxis={"range": [min(yy), max(yy)], "autorange": False},
                xaxis={"range": [xrange0, xrange1], "autorange": False}
            )

            # Update ophys trace
            timeseries = self.ophys_trace
            istart = timeseries_time_to_ind(timeseries, time_window[0])
            istop = timeseries_time_to_ind(timeseries, time_window[1])
            yy, units = get_timeseries_in_units(timeseries, istart, istop)
            xx = get_timeseries_tt(timeseries, istart, istop)
            self.traces.data[1].x = xx
            self.traces.data[1].y = list(yy)
            self.traces.update_layout(
                yaxis3={"range": [min(yy), max(yy)], "autorange": False},
                xaxis3={"range": [xrange0, xrange1], "autorange": False}
            )

            # Update spikes traces
            self.update_spike_traces(time_window=time_window)
            self.traces.update_layout(
                xaxis2={"range": [xrange0, xrange1], "autorange": False}
            )

            # Update frame trace
            self.start_frame_x = (xrange1 + xrange0) / 2
            self.traces.update_layout(
                shapes=[{
                    'type': 'line',
                    'x0': (xrange1 + xrange0) / 2,
                    'x1': (xrange1 + xrange0) / 2,
                    'xref': 'x',
                    'y0': -1000,
                    'y1': 1000,
                    'yref': 'paper',
                    'line': {
                        'width': 4,
                        'color': 'rgb(30, 30, 30)'
                    }
                }]
            )

            return {'display': 'inline-block'}, self.traces

        @self.parent_app.callback(
            [
                Output('button_file_browser_allen-dash', 'n_clicks'),
                Output('slider_start_time', 'value'),
                Output('div-controller', 'style'),
                Output('div-photon-series', 'children'),
                Output('external-update-max-time-trigger', 'children')
            ],
            [Input('submit-filebrowser-allen-dash', component_property='n_clicks')],
            [State('chosen-filebrowser-allen-dash', 'value')]
        )
        def load_nwb_file(click, path):
            if click:
                if Path(Path(self.parent_app.server.config['DATA_PATH']).parent / path).is_file() and path.endswith('.nwb'):
                    self.path_nwb = str(Path(self.parent_app.server.config['DATA_PATH']).parent / path)
                    self.render_dashboard()

                    display = {'display': 'block'}
                    self.controller_time.tmax = self.controller_tmax

                    return 1, self.controller_tmin, display, self.photon_series, str(np.random.rand())
            else:
                raise dash.exceptions.PreventUpdate()

        @self.parent_app.callback(
            [Output(component_id='figure_photon_series', component_property='figure')],
            [
                Input(component_id='figure_traces', component_property='relayoutData'),
                Input('figure_traces', 'figure'),
                Input({'type': 'pixelmask_button', 'index': ALL}, 'n_clicks')
            ]
        )
        def change_frame(relayoutData, figure, click):
            """
            Update tiff frame with change on:
              - Figure data
              - Frame selector position
            """

            ctx = dash.callback_context
            trigger_source = ctx.triggered[0]['prop_id'].split('.')[1]

            if trigger_source == 'n_clicks' and click and click[0] is not None:
                self.photon_series.graph.update_pixelmask()
                return [self.photon_series.graph.out_fig]

            if relayoutData is not None and "shapes[0].x0" in relayoutData and trigger_source == 'relayoutData':
                pos = relayoutData["shapes[0].x0"]
            else:
                pos = self.start_frame_x

            self.photon_series.graph.update_image(pos, self.nwb, self.path_nwb)

            return [self.photon_series.graph.out_fig]

    def render_dashboard(self):
        io = pynwb.NWBHDF5IO(self.path_nwb, 'r')
        self.nwb = io.read()
        self.controller_tmax = get_timeseries_maxt(self.nwb.processing['ophys'].data_interfaces['fluorescence'].roi_response_series['roi_response_series'])
        self.controller_tmin = get_timeseries_mint(self.nwb.processing['ophys'].data_interfaces['fluorescence'].roi_response_series['roi_response_series'])

        # Create traces figure
        self.traces = make_subplots(rows=3, cols=1, row_heights=[0.4, 0.2, 0.4],
                                    shared_xaxes=False, vertical_spacing=0.02)

        # Electrophysiology
        self.ecephys_trace = self.nwb.processing['ecephys'].data_interfaces['filtered_membrane_voltage']
        self.traces.add_trace(
            go.Scattergl(
                x=[0],
                y=[0],
                line={"color": "#151733", "width": 1},
                mode='lines',
            ),
            row=1, col=1
        )

        # Optophysiology
        self.ophys_trace = self.nwb.processing['ophys'].data_interfaces['fluorescence'].roi_response_series['roi_response_series']
        self.traces.add_trace(
            go.Scattergl(
                x=[0],
                y=[0],
                line={"color": "#151733", "width": 1},
                mode='lines'),
            row=3, col=1
        )

        # Layout
        self.traces.update_layout(
            height=400, showlegend=False, title=None,
            paper_bgcolor='rgba(0, 0, 0, 0)', plot_bgcolor='rgba(0, 0, 0, 0)',
            margin=dict(l=60, r=20, t=8, b=20),
            shapes=[{
                'type': 'line',
                'x0': 10,
                'x1': 10,
                'xref': 'x',
                'y0': -1000,
                'y1': 1000,
                'yref': 'paper',
                'line': {
                    'width': 4,
                    'color': 'rgb(30, 30, 30)'
                }
            }]
        )
        self.traces.update_xaxes(patch={
            'showgrid': False,
            'visible': False,
        })
        self.traces.update_xaxes(patch={
            'visible': True,
            'showline': True,
            'linecolor': 'rgb(0, 0, 0)',
            'title_text': 'time [s]'},
            row=3, col=1
        )
        self.traces.update_yaxes(patch={
            'showgrid': False,
            'visible': True,
            'showline': True,
            'linecolor': 'rgb(0, 0, 0)'
        })
        self.traces.update_yaxes(
            patch={
                "title": {"text": "Ephys [V]", "font": {"color": "#151733", "size": 16}}
            },
            row=1, col=1
            )
        self.traces.update_yaxes(
            patch={
                "title": {"text": "dF/F", "font": {"color": "#151733", "size": 16}}
            },
            row=3, col=1)

        self.traces.update_yaxes(patch={
            "title": {"text": "Spikes", "font": {"color": "#151733", 'size': 16}},
            "showticklabels": True,
            "ticks": "outside",
            "tickcolor": "white",
            "color": "white",

            },
            row=2, col=1
        )

        # Two photon imaging
        self.photon_series = TiffImageSeriesComponent(
            id='figure_photon_series',
            parent_app=self.parent_app,
            imageseries=self.nwb.acquisition['raw_ophys'],
            path_external_file=None,
            pixel_mask=self.nwb.processing['ophys'].data_interfaces['image_segmentation'].plane_segmentations['plane_segmentation'].pixel_mask[:],
            foreign_time_window_controller=self.controller_time,
        )

        self.photon_series.graph.out_fig.update_layout(
            showlegend=False,
            margin=dict(l=10, r=10, t=70, b=70),
            # width=300, height=300,
        )

    def update_spike_traces(self, time_window):
        """Updates list of go.Scatter objects at spike times"""
        self.spike_traces = []
        t_start = time_window[0]
        t_end = time_window[1]
        all_spikes = self.nwb.units['spike_times'][0]
        mask = (all_spikes > t_start) & (all_spikes < t_end)
        selected_spikes = all_spikes[mask]
        # Makes a go.Scatter object for each spike in chosen interval
        for spkt in selected_spikes:
            self.traces.add_trace(go.Scattergl(
                x=[spkt, spkt],
                y=[-1000, 1000],
                line={"color": "gray", "width": .5},
                mode='lines'),
                row=2, col=1
            )
