import os

import dash_bootstrap_components as dbc
from dash import Dash
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize the Dash app
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Basic layout
app.layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader("Trading Dashboard"),
                                dbc.CardBody(["Welcome to the Trading Dashboard"]),
                            ]
                        )
                    ]
                )
            ]
        )
    ]
)

if __name__ == "__main__":
    # Run the app using the current API
    app.run(debug=True, host="0.0.0.0", port=8050)
