import base64
import datetime
import io

import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from dash import dcc, html, dash_table

df = px.data.gapminder()

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']


def Header(name, app):
    """
    Create header for app
    :param name:
    :param app:
    :return: dash_bootstrap_components
    """
    title = html.H1(name, style={"margin-top": 15})
    logo = html.Img(
        src="assets/logo.png", style={"float": "left", "height": 40,
                                      "margin-top": 20, "margin-left": 20, "margin-right": 20}
    )
    return dbc.Row([dbc.Col([logo, title])])


def drag_drop_spreadsheet_contents():
    """
    Create drag and drop area for spreadsheet
    :return: dah_html_components.Div
    """
    return html.Div([
        dcc.Upload(
            id='upload-data',
            children=html.Div([
                'Drag and Drop or ',
                html.A('Select Files')
            ]),
            style={
                'width': '100%',
                'height': '60px',
                'lineHeight': '60px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'margin': '10px'
            },
            # Allow multiple files to be uploaded
            multiple=True
        ),
        html.Div(id='output-data-upload',
                 # allow slide if overflow
                 style={'overflow': 'auto', 'height': '500px'}
                 ),
    ])


def parse_contents(contents, filename, date):
    """
    Parse contents of uploaded file

        Args:
            contents (str): Contents of the uploaded file
            filename (str): Name of the uploaded file
            date (str): Date of the uploaded file

        Returns:
            df.to_json (json): Dataframe of the uploaded file in json format
            children (dash_html_components.Div): Children to be displayed

    """
    content_type, content_string = contents.split(',')

    decoded = base64.b64decode(content_string)
    try:
        if 'csv' in filename:
            # Assume that the user uploaded a CSV file
            df = pd.read_csv(
                io.StringIO(decoded.decode('utf-8')))

        elif 'xls' in filename:
            # Assume that the user uploaded an excel file
            df = pd.read_excel(io.BytesIO(decoded))

        else:
            df = px.data.gapminder()

    except Exception as e:
        print(e)
        return html.Div([
            'There was an error processing this file.'
        ])

    children = html.Div([
        html.H5(filename),
        html.H6(datetime.datetime.fromtimestamp(date)),

        dash_table.DataTable(
            df.to_dict('records'),
            [{'name': i, 'id': i} for i in df.columns]
        ),

        html.Hr(), # horizontal line

        # For debugging, display the raw contents provided by the web browser
        html.Div('Raw Content'),
        html.Pre(contents[0:200] + '...', style={
            'whiteSpace': 'pre-wrap',
            'wordBreak': 'break-all'
        }),
    ])

    return df.to_json(orient='split'), children

