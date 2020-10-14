import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from pathlib import Path
from nwbwidgets.utils.timeseries import (get_timeseries_maxt, get_timeseries_mint)
from nwbwidgets.ophys import compute_outline
from tifffile import imread, TiffFile
import plotly.graph_objects as go
from .utils import get_fix_path
import numpy as np


class TiffImageSeriesComponent(html.Div):
    """Div containing tiff image graph and pixelmask button"""
    def __init__(self, id, parent_app, imageseries, path_external_file=None, pixel_mask=None,
                 foreign_time_window_controller=None):
        super().__init__()

        self.graph = TiffImageSeriesGraphComponent(id=id, parent_app=parent_app, imageseries=imageseries, path_external_file=path_external_file, pixel_mask=pixel_mask,foreign_time_window_controller=foreign_time_window_controller)
        self.pixelmask_btn = dbc.Button('Pixel Mask', id={'type': 'pixelmask_button', 'index': f'mask_btn_{id}'})

        self.children = dbc.Row([
            dbc.Col(
                dbc.Card([
                    dbc.CardBody([
                        self.graph,
                        self.pixelmask_btn
                    ], style={'justify-content': 'center', 'text-align': 'center'}),
                ]),
                width={'size': 12},
            ),
        ])


class TiffImageSeriesGraphComponent(dcc.Graph):
    """Component that renders specific frame of a Tiff file"""
    def __init__(self, parent_app, imageseries, path_external_file=None, pixel_mask=None,
                 foreign_time_window_controller=None, id='tiff_image_series'):
        super().__init__(id=id, figure={}, config={'displayModeBar': False})
        self.parent_app = parent_app
        self.imageseries = imageseries
        self.pixel_mask = pixel_mask
        self.parent_files_path = Path(self.parent_app.server.config['DATA_PATH']).parent

        if foreign_time_window_controller is not None:
            self.time_window_controller = foreign_time_window_controller
        else:
            self.time_window_controller = None

        # Set controller
        if foreign_time_window_controller is None:
            tmin = get_timeseries_mint(imageseries)
            tmax = get_timeseries_maxt(imageseries)
            # self.time_window_controller = StartAndDurationController(tmax, tmin)
        else:
            self.time_window_controller = foreign_time_window_controller

        # Make figure component
        if path_external_file is not None:
            self.tiff = TiffFile(path_external_file)
            self.n_samples = len(self.tiff.pages)
            self.page = self.tiff.pages[0]
            self.n_y, self.n_x = page.shape

            # Read first frame
            self.image = imread(path_external_file, key=0)
        else:
            self.image = []
            self.tiff = None

        self.out_fig = go.Figure(
            data=go.Heatmap(
                z=self.image,
                colorscale='gray',
                showscale=False,
            ), 
        )
        self.out_fig.update_layout(
            xaxis=go.layout.XAxis(showticklabels=False, ticks=""),
            yaxis=go.layout.YAxis(showticklabels=False, ticks=""),
        )

        self.figure = self.out_fig


    def update_image(self, pos, nwb, relative_path):
        """Update tiff image frame"""

        frame_number = int(pos * nwb.acquisition['raw_ophys'].rate)
        path_external = str(Path(relative_path).parent / Path(nwb.acquisition['raw_ophys'].external_file[0]))
        path_external_file = get_fix_path(path_external)

        if self.tiff is None:
            self.tiff = TiffFile(path_external_file)
            self.n_samples = len(self.tiff.pages)
            self.page = self.tiff.pages[0]
            n_y, n_x = self.page.shape
            self.pixel_mask = nwb.processing['ophys'].data_interfaces['image_segmentation'].plane_segmentations['plane_segmentation'].pixel_mask[:]

            mask_matrix = np.zeros((n_y, n_x))
            for px in self.pixel_mask:
                mask_matrix[px[1], px[0]] = 1

            self.mask_x_coords, self.mask_y_coords = compute_outline(image_mask=mask_matrix, threshold=0.9)

        self.image = imread(path_external_file, key=frame_number)
        self.out_fig.data[0].z = self.image

        self.out_fig.update_layout(
            autosize=False,
            margin=dict(
                l=0,
                r=0,
                b=10,
                t=0,
                pad=0
            ),
            height=380,
            
        )

    def update_pixelmask(self):
        """ Update pixel mask on self figure """

        if len(self.out_fig.data) == 1:
            trace = go.Scatter(
                x=self.mask_x_coords,
                y=self.mask_y_coords,
                fill='toself',
                mode='lines',
                line={"color": "rgb(219, 59, 59)", "width": 2},
            )
            self.out_fig.add_trace(trace)
        else:
            if self.out_fig.data[1].x == self.mask_x_coords and self.out_fig.data[1].y == self.mask_y_coords:
                self.out_fig.data[1].x = []
                self.out_fig.data[1].y = []
            else:
                self.out_fig.data[1].x = self.mask_x_coords
                self.out_fig.data[1].y = self.mask_y_coords