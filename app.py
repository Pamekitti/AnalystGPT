import json
from textwrap import dedent

import dash
import dash_bootstrap_components as dbc
import openai
import pandas as pd
import plotly.express as px
from dash import html, dcc, dash_table
from dash.dependencies import Input, Output, State

from config.api import openai_api_key
from utils.dashboard_utils import Header, drag_drop_spreadsheet_contents, parse_contents

# Authentication
openai.api_key = openai_api_key

# Create
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

content_style = {"height": "475px"}

chat_input = dbc.InputGroup(
    [
        dbc.Input(
            id="input-text", placeholder="What do you what to see about your data?"
        ),
        dbc.InputGroupAddon(
            dbc.Button("Submit", id="button-submit", color="primary"),
            addon_type="append",
        ),
    ]
)
output_graph = [
    dbc.CardHeader("AI Generated Insight"),
    dbc.CardBody(dbc.Spinner(dcc.Graph(id="output-graph", style={"height": "425px"}))),
]
output_code = [
    dbc.CardHeader("Chat Interface"),
    dbc.CardBody(
        dbc.Spinner(dcc.Markdown("", id="conversation-interface")),
        style={"height": "725px", "overflow": "auto"},
    ),
]

explanation_card = [
    dbc.CardHeader("Upload Your Spreadsheet File"),
    dbc.CardBody(
        html.Div([
            drag_drop_spreadsheet_contents()
        ])
    ),
]

left_col = [dbc.Card(output_graph), html.Br(), dbc.Card(explanation_card)]

right_col = [dbc.Card(output_code), html.Br(), chat_input]

app.layout = dbc.Container(
    [
        dcc.Store(id="spreadsheet-data"),
        Header("AnalystGPT", app),
        html.Hr(),
        dbc.Row([dbc.Col(left_col, md=7), dbc.Col(right_col, md=5)]),
    ],
    fluid=True,
)


@app.callback(
    [Output('output-data-upload', 'children'),
     Output('spreadsheet-data', 'data')],
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
    State('upload-data', 'last_modified'))
def update_output(list_of_contents, list_of_names, list_of_dates):
    """
    Update spreadsheet data when a file is uploaded through drag and drope

        Args:
            list_of_contents (list): List of contents of the uploaded files
            list_of_names (list): List of names of the uploaded files
            list_of_dates (list): List of dates of the uploaded files

        Returns:
            childrens (list): List of childrens to be displayed
            schema (dict): Dictionary of the uploaded files
    """
    if list_of_contents is not None:
        schema = {}
        childrens = []
        for c, n, d in zip(list_of_contents, list_of_names, list_of_dates):
            data, children = parse_contents(c, n, d)
            childrens.append(children)
            schema['n'] = data
        return childrens, json.dumps(schema)

    else:
        df = px.data.gapminder()
        children = html.Div([html.H5("Example Data: Gapminder"),
                             dash_table.DataTable(
                                 df.to_dict('records'),
                                 [{'name': i, 'id': i} for i in df.columns]
                             )
                             ])
        return children, json.dumps({'gapminder': df.to_json(orient='split')})


@app.callback(
    [Output("output-graph", "figure"),
     Output("conversation-interface", "children"),
     Output("input-text", "value")],
    [Input("spreadsheet-data", "data"),
     Input("button-submit", "n_clicks"),
     Input("input-text", "n_submit")],
    [State("input-text", "value"),
     State("conversation-interface", "children")],
)
def generate_graph(data, n_clicks, n_submit, text, conversation):
    """
    Steps:
    1. User type what he/she wants to see about the data
    2. Generate prompt language model
    3. Generate Completion through OpenAI API
    4. Generate graph based on language model completion
    5. Update the conversation interface

        Args:
            data (str): Data of the uploaded file
            n_clicks (int): Number of clicks on the submit button
            n_submit (int): Number of submit on the input
            text (str): Text of the input text
            conversation (str): Text of the conversation interface

        Returns:
            fig (plotly.graph_objects.Figure): Figure of the generated graph
            conversation (str): Text of the conversation interface
            text (str): Text of the input text
    """
    # TODO: Only allow the first uploaded table for this version
    ds = json.loads(data)
    for k, v in ds.items():
        df = pd.read_json(v, orient='split')
        pass

    # Define the prompt
    if k == 'gapminder':
        prompt = f"""
            Our dataframe "df" columns contain: country, continent, year, life expectancy (lifeExp), population (pop), GDP per capita (gdpPercap), the ISO alpha, the ISO numerical.
    
            **Description**: The life expectancy in Oceania countries throughout the years.
    
            **Code**: ```px.line(df.query("continent == 'Oceania'"), x='year', y='lifeExp', color='country', log_y=False, log_x=False)```
            """
    else:
        prompt = f"""
            Our dataframe "df" columns contain: {', '.join(df.columns)}.
            Use plotly express library to generate a graph in python.
            Only provide ```px.line()``` function. 
            Important!! One line of code is enough!! Just provide the px function that's it.
            
            **Description**: Number of {df.columns[0]} by {df.columns[1]}
            
            **Code**: ```px.histogram(df, x= "{df.columns[1]}")```
        """
        # TODO: Maybe provide negative prompt to limit the output

    if n_clicks is None and n_submit is None:
        fig = px.line(title="Please tell me what you want to see about your data")
        fig.update_layout(
            template="plotly_white",
            margin=dict(l=0, r=0, t=30, b=0),
        )

        return fig, dash.no_update, dash.no_update

    conversation += dedent(
        f"""
    **Description**: {text}

    **Code**:"""
    )

    gpt_input = (prompt + conversation).replace("```", "").replace("**", "")
    print(gpt_input)
    print("-" * 40)

    response = openai.Completion.create(
        engine="code-davinci-002",
        prompt=gpt_input,
        max_tokens=200,
        stop=["Description:", "Code:"],
        temperature=0,
        top_p=1,
        n=1,
    )

    output = response.choices[0].text.strip()

    # Make sure that output only contains 1 function px.
    output = "px." + output.split("px.")[1]
    output = output.split("\n")[0]
    print(output)
    conversation += f" ```{output}```\n"

    try:
        fig = eval(output)
        fig.update_layout(
            template="plotly_white",
            margin=dict(l=0, r=0, t=30, b=0),
        )
    except Exception as e:
        fig = px.line(title=f"Exception: {e}. Please try again!")

    return fig, conversation, ""


if __name__ == "__main__":
    app.run_server(debug=False, host='0.0.0.0', port='80')
