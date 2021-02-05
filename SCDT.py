##Scrapping City Data Toolbox
import pandas as pd
import numpy as np
from shapely.geometry import shape,Point
import requests
from math import pi,sqrt,cos
import time

def grid_condition(polygon,point,xstep,ystep):
    if polygon.contains(Point(point)):
        return True
    else:
        x,y = point[0],point[1]
        pts = [(x-xstep,y),(x+xstep,y),(x,y-ystep),(x,y+ystep)]
        return any([polygon.contains(Point(i)) for i in pts])

#receives a city polygon and returns a grid of searchable points
def make_grid(city_polygon,radius):
    step = (180/pi)*((radius*sqrt(2))/(6.378e6))
    if np.sign(city_polygon.bounds[1]) == np.sign(city_polygon.bounds[3]):
        cmax = max(cos(city_polygon.bounds[1]*(pi/180)),cos(city_polygon.bounds[3]*(pi/180)))
    else:
        cmax = 1
    print(cmax)
    xs = np.arange(city_polygon.bounds[0],city_polygon.bounds[2],step/cmax)
    ys = np.arange(city_polygon.bounds[1],city_polygon.bounds[3],step)
    print(len(xs),len(ys))
    grid = [(i,j) for j in ys for i in xs]
    grid = [point for point in grid if grid_condition(city_polygon,point,step/cmax,step)]
    return grid



#receives a Foursquare rawdata and return a clean DataFrame
def clean_data(venues):
    venues_filt = pd.DataFrame()
    venues_filt['name'] = venues.loc[:, 'venue.name']
    venues_filt['categories'] = [i[0]['name'] for i in venues['venue.categories']]
    venues_filt['coordinates'] = [(venues['venue.location.lng'][i],venues['venue.location.lat'][i]) for i in range(len(venues))]
    return(venues_filt)

#do the Foursquare API serch around a point
def collect_Data(xpoint,radius,fsCredential):
    cID, cSECRET, fsVERSION = fsCredential
    LIMIT = 100
    latitude,longitude = xpoint[1],xpoint[0]
    url = 'https://api.foursquare.com/v2/venues/explore?&client_id={}&client_secret={}&v={}&ll={},{}&radius={}&limit={}'.format(
            cID, cSECRET, fsVERSION, latitude, longitude, radius, LIMIT)
    rawdata = requests.get(url).json()
    venues = pd.json_normalize(rawdata['response']['groups'][0]['items'])
    if venues.empty:
        return venues
    else:
        return clean_data(venues)
    
#fixing a no show
def recerrorfix(point,radius,credential):
    time.sleep(1+np.random.rand())
    key = input('Something went wrong, the software failed to obtain data around {}. Press any key to try again, this will call the Foursquare API one additional time'.format(point))
    try:
        a = collect_Data(point,radius,credential)
    except:
        return recerrorfix(point,radius,credential)
    return a
                         
#given a grid does the search around each point and return a pandas dataframe with all venues in the space represented by the grid.    
def gather_fsdata(grid,radius,credential):
    data=pd.DataFrame()
    cancel_question = input('This will make up to {} calls in your Foursquare API, do you wish to proceed? Press "C" to cancel'.format(len(grid)))
    if cancel_question == 'C':
        return 0
    for point in grid:
        try:
            a = collect_Data(point,radius,credential)
        except:
            a = recerrorfix(point,radius,credential)
        if not a.empty:
            data = data.append(a)
            print(data.shape)
            if a.shape[0]>99: #Failsafe in case the API returns 100 venues.
                print('A query returned 100 venues or more')
                lon,lat = point[0],point[1]
                
                miniradius = radius/sqrt(2)
                ystep = (180/pi)*(miniradius/(6.378e6))
                xstep = ystep/cos(lat*pi/180)
                minigrid = [(lon-xstep,lat),(lon+xstep,lat),(lon,lat-ystep),(lon,lat+xstep)]
                
                b = gather_fsdata(minigrid,1.1*miniradius,credential)
                data = data.append(b)
                


    data=data.drop_duplicates(ignore_index=True)
    print(data.shape)
    return data