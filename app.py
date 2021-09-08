import os
import json
import requests

import dash
from dash import html
from dash import dcc
import plotly.graph_objects as go

from dash.dependencies import (Input, Output)



external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
# app.config['suppress_callback_exceptions'] = True
app.title = 'Foursquare API Testing'
server = app.server

#################################################################################

### ORS Token
with open(file='ors_token.txt', mode='r') as ors:
    ors_api_key = ors.read()

### Mapbox API
with open(file='mapbox_token.txt', mode='r') as mbox:
    map_api_key = mbox.read()

### Read `foursquare` Venues
with open(file='foursquare_venue_categories.json', mode='r') as fcfile:
    foursquare_venues = json.load(fp=fcfile)

### Read `foursquare` Credentials
with open(file='foursquare_credentials.json', mode='r') as creds:
    fcreds = json.load(fp=creds)

# Extract main categories (keys and values)
main_category_keys = [list(i['main_category'].keys())[0] for i in foursquare_venues['foursquare_venues']]
main_category_values = [list(i['main_category'].values())[0] for i in foursquare_venues['foursquare_venues']]
main_category_keys_values = dict(zip(main_category_keys, main_category_values))

# Extract sub-categories
def extract_subcategories(main_category, main_category_keys, data):
    if not (main_category in main_category_keys):
        return {}
    
    data_list = data['foursquare_venues']
    for i in data_list:
        if (main_category == list(i['main_category'].keys())[0]):
            sub_categories = i['sub_categories']
            break
        else:
            continue
    
    return sub_categories

# Extract device location
def get_device_loc():
    ip_url = 'http://ip-api.com/json'
    default_loc_req = requests.get(url=ip_url)
    default_loc_data = default_loc_req.json() if default_loc_req.status_code == 200 else {}
    default_loc = default_loc_data['city']
    return default_loc

# Extract the coordinates for any place
def geocode(place, api_key=ors_api_key):
    ors_url = 'https://api.openrouteservice.org/geocode/search?api_key={}&text={}'
    ors_url = ors_url.format(api_key, place)
    
    headers = {
        'Accept' : 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
    }

    req = requests.get(url=ors_url, headers=headers)
    # print('Geocode response status - {} : {} {}'.format(place, req.status_code, req.reason))

    if (req.status_code == 200):
        req_data = req.json()
        features = req_data['features']
        # format - [longitude, latitude]
        coords = features[0]['geometry']['coordinates']
        return coords[::-1]

    return None

#################################################################################


app.layout = html.Div([
    html.Meta(charSet='UTF-8'),
    html.Meta(name='viewport', content='width=device-width, initial-scale=1.0'),

    html.Div([

        html.Div([
            html.Div([
                html.H6('Main Category'),
                dcc.Dropdown(
                    id='select-main-category', 
                    options=[{'label' : i, 'value' : i} for i in main_category_keys]
                )
            ], className='six columns'),

            html.Div([
                html.H6('Sub Category'),
                dcc.Dropdown(id='select-sub-category')
            ], className='six columns'),
        ], className='row'),
    
        html.Div([
            
            html.Div([
                html.P('Place Name'),
            ], className='six columns', style={'textAlign' : 'right'}),

            html.Div([
                dcc.Input(id='place-location', type='text', value=get_device_loc(), debounce=True)
            ], className='six columns', style={'textAlign' : 'left'})

        ], className='row', style={'textAlign' : 'center', 'paddingTop' : 30, 'paddingBottom' : 30}),

    ], className='container'),

    html.Div(id='map-content')
])


@app.callback(
    Output('select-sub-category', 'options'),
    [Input('select-main-category', 'value')]
)
def get_sub_category_options(value):
    sckv = extract_subcategories(
        main_category=value, main_category_keys=main_category_keys, data=foursquare_venues
    )
    option_list = [{'label' : l, 'value' : l} for l in sckv]
    return option_list

@app.callback(
    Output('map-content', 'children'),
    [Input('select-main-category', 'value'), Input('select-sub-category', 'value'), Input('place-location', 'value')]
)
def get_url(main_category, sub_category, place_name):
    error_statement = html.P('Please select the dropdown value...', style={'padding' : 100, 'textAlign' : 'center'})
    try:
        if not sub_category:
            return error_statement
        if not main_category:
            return error_statement

        sckv = extract_subcategories(
            main_category=main_category, main_category_keys=main_category_keys, data=foursquare_venues
        )

        category_id = sckv[sub_category]

        center_lat, center_lon = geocode(place=place_name)
        client_id = fcreds['CLIENT_ID']
        client_secret = fcreds['CLIENT_SECRET']
        limit = 10
        version = fcreds['VERSION']

        foursquare_url = fcreds['URL']
        foursquare_url = foursquare_url.format(center_lat, center_lon, category_id, client_id, client_secret, limit, version)

        venue_result = requests.get(url=foursquare_url).json()['response']['venues']
        names = []; categories = []; lats = []; lons=[]; hover_texts = []

        for res in range(len(venue_result)):
            name = venue_result[res]['name']
            category = venue_result[res]['categories'][0]['pluralName']
            location = venue_result[res]['location']
            latitude = venue_result[res]['location']['lat']
            longitude = venue_result[res]['location']['lng']

            names.append(name)
            categories.append(category)
            lats.append(latitude)
            lons.append(longitude)
            hover_texts.append('{}; {}'.format(name, category))

        trace = go.Scattermapbox(
            lat=lats,
            lon=lons,
            mode='markers',
            marker=dict(
                size=10,
                color='red'
            ),
            text=hover_texts,
            hoverinfo='text'
        )

        layout = go.Layout(
            autosize=True,
            height=600,
            hovermode='closest',
            showlegend=False,
            mapbox=dict(
                accesstoken=map_api_key,
                bearing=0,
                center=dict(
                    lat=center_lat,
                    lon=center_lon
                ),
                pitch=0,
                zoom=8,
                style='outdoors'
            ),
            margin=dict(l=40, r=40, t=40, b=40)
        )

        fig = go.Figure(data=[trace], layout=layout)

        return html.Div([
            dcc.Graph(
                id='map-plot',
                figure=fig
            )
        ])

    except Exception as e:
        return error_statement




if __name__ == '__main__':
    app.run_server(debug=True)